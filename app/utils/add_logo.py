import io
import re
import tempfile
from urllib.parse import unquote, urlparse

import boto3
import cv2
import numpy as np
import requests
from PIL import Image

from core.config import config


class LogoOverlay:
    def __init__(self, video_url: str | None = None, img_url: str | None = None):
        aws_session = boto3.Session(
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=config.AWS_REGION_NAME,
        )

        self.video_url = video_url
        self.img_url = img_url
        self.logo_url = config.VISU_LOGO_URL
        self.bucket_name = config.AWS_CUSTOMER_INCIDENTS_BUCKET_NAME
        self.s3_client = aws_session.client("s3")

    def upload_to_s3(self, file, filename: str, extra_args=None):
        self.s3_client.upload_fileobj(
            file, self.bucket_name, filename, ExtraArgs=extra_args or {}
        )

    @staticmethod
    def robust_text_detection(gray):
        h, w = gray.shape

        # MSER text candidates
        mser = cv2.MSER_create(5, 60, 8000)
        regions, _ = mser.detectRegions(gray)
        mser_mask = np.zeros_like(gray)

        for pts in regions:
            hull = cv2.convexHull(pts.reshape(-1, 1, 2))
            cv2.drawContours(mser_mask, [hull], -1, 255, -1)

        # MORPH close for bright captions/timestamps
        _, th = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), 2)

        # Edge-based SWT-like reinforcement
        edges = cv2.Canny(gray, 60, 180)
        swt_mask = cv2.bitwise_and(edges, th)

        combined = cv2.bitwise_or(mser_mask, th)
        combined = cv2.bitwise_or(combined, swt_mask)

        contours, _ = cv2.findContours(
            combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        boxes = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w < 20 or h < 10:
                continue
            if w / h > 15 or h / w > 15:
                continue
            boxes.append((x, y, x + w, y + h))

        return boxes

    @staticmethod
    def detect_motion_map(prev, curr):
        diff = cv2.absdiff(prev, curr)
        g = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        g = cv2.GaussianBlur(g, (7, 7), 0)
        _, th = cv2.threshold(g, 25, 255, cv2.THRESH_BINARY)
        return th

    @staticmethod
    def detect_existing_logo(frame, corner_ratio=0.2):
        h, w = frame.shape[:2]
        cw, ch = int(w * corner_ratio), int(h * corner_ratio)

        ROIs = {
            "TL": frame[0:ch, 0:cw],
            "TR": frame[0:ch, w - cw: w],
            "BL": frame[h - ch: h, 0:cw],
            "BR": frame[h - ch: h, w - cw: w],
        }

        detected = []

        for name, roi in ROIs.items():
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            # Edge density: logos have high edges
            edges = cv2.Canny(gray, 80, 160)
            edge_val = edges.sum() / 255

            # Color variance: logos have sharp colors
            var = np.var(roi)

            if edge_val > 1500 or var > 2000:
                detected.append(name)

        return detected

    @staticmethod
    def score_corner(frame, x, y, ow, oh, text_boxes, motion_map=None):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = x, y, x + ow, y + oh
        if x2 > w or y2 > h:
            return 1e12

        score = 0

        # TEXT OVERLAP PENALTY
        for tx1, ty1, tx2, ty2 in text_boxes:
            ix = max(0, min(x2, tx2) - max(x1, tx1))
            iy = max(0, min(y2, ty2) - max(y1, ty1))
            score += ix * iy * 200

        # Edge clutter penalty
        roi = frame[y1:y2, x1:x2]
        g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(g, 80, 160)
        score += edges.sum() // 50

        # Motion penalty
        if motion_map is not None:
            mroi = motion_map[y1:y2, x1:x2]
            score += mroi.sum() // 20

        return score

    @staticmethod
    def find_safest_corner(
        frame, ow, oh, text_boxes, motion_map, existing_logos, margin=30
    ):
        h, w = frame.shape[:2]
        corners = {
            "TL": (margin, margin),
            "TR": (w - ow - margin, margin),
            "BL": (margin, h - oh - margin),
            "BR": (w - ow - margin, h - oh - margin),
        }

        best_corner = None
        best_score = 1e18

        for cname, (x, y) in corners.items():
            # DO NOT use a corner with an existing logo
            if cname in existing_logos:
                continue

            s = LogoOverlay.score_corner(frame, x, y, ow, oh, text_boxes, motion_map)
            if s < best_score:
                best_score = s
                best_corner = (x, y)

        return best_corner

    def get_logo_overlay(self):
        response = requests.get(self.logo_url)
        pil_logo = Image.open(io.BytesIO(response.content))
        if pil_logo.mode in ("L", "P"):
            pil_logo = pil_logo.convert("RGBA")
        overlay = cv2.cvtColor(np.array(pil_logo), cv2.COLOR_RGBA2BGRA)
        return overlay

    def resize_logo(self, overlay, h, w):
        oh, ow = overlay.shape[:2]
        scale = min((w // 6) / ow, (h // 6) / oh, 1.0)
        overlay = cv2.resize(overlay, (int(ow * scale), int(oh * scale)))
        return overlay


class VideoLogoOverlay(LogoOverlay):
    def __init__(self, video_url: str):
        super().__init__(video_url=video_url)

    def process_video(self):
        if not self.video_url:
            raise ValueError("Video not specified")

        # Get logo overlay
        overlay = self.get_logo_overlay()

        # Open video
        cap = cv2.VideoCapture(self.video_url)
        ret, frame1 = cap.read()
        if not ret:
            raise Exception("Could not read video.")

        h, w = frame1.shape[:2]
        overlay = self.resize_logo(overlay, h, w)
        oh, ow = overlay.shape[:2]

        # Sample first 3 frames for stable text detection
        frames = [frame1]
        for _ in range(2):
            ret, f = cap.read()
            if ret:
                frames.append(f)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Multi-frame text detection
        text_boxes = []
        for f in frames:
            gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            text_boxes.extend(LogoOverlay.robust_text_detection(gray))

        # Detect existing logos in corners
        existing_logos = LogoOverlay.detect_existing_logo(frame1)

        # Motion map (first two frames)
        motion_map = LogoOverlay.detect_motion_map(frames[0], frames[1])

        # Pick safest corner
        pos = LogoOverlay.find_safest_corner(
            frame1, ow, oh, text_boxes, motion_map, existing_logos
        )
        if pos is None:
            pos = (w - ow - 30, h - oh - 30)
        logo_x, logo_y = pos

        # Prepare output temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            fps = cap.get(cv2.CAP_PROP_FPS) or 24  # fallback if FPS unavailable
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(tmp.name, fourcc, fps, (w, h))

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Alpha blending
                alpha = overlay[:, :, 3] / 255.0
                roi = frame[logo_y: logo_y + oh, logo_x: logo_x + ow]
                frame[logo_y: logo_y + oh, logo_x: logo_x + ow] = overlay[
                    :, :, :3
                ] * alpha[..., None] + roi * (1 - alpha[..., None])

                out.write(frame)

            out.release()
            cap.release()

            # Extract filename robustly
            path = urlparse(self.video_url).path
            filename = unquote(path.split("/")[-1]).replace(".mp4", "_share.mp4")

            with open(tmp.name, "rb") as file:
                self.upload_to_s3(file, filename, {"ContentType": "video/mp4"})

        new_path = "https://" + config.AWS_CUSTOMER_INCIDENTS_CLOUDFRONT_URL + "/" + filename
        return new_path


class ImageLogoOverlay(LogoOverlay):
    def __init__(self, img_url: str):
        super().__init__(img_url=img_url)

    def process_image(self):
        if not self.img_url:
            raise ValueError("Image not specified")

        # Get logo overlay
        overlay = self.get_logo_overlay()

        # Load image
        response = requests.get(self.img_url)
        pil_img = Image.open(io.BytesIO(response.content))
        if pil_img.mode in ("L", "P"):
            pil_img = pil_img.convert("RGBA")
        frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGR)

        h, w = frame.shape[:2]
        overlay = self.resize_logo(overlay, h, w)
        oh, ow = overlay.shape[:2]

        # Detect text
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        text_boxes = LogoOverlay.robust_text_detection(gray)

        # Detect existing logos in corners
        existing_logos = LogoOverlay.detect_existing_logo(frame)

        # Pick safest corner
        pos = LogoOverlay.find_safest_corner(
            frame, ow, oh, text_boxes, motion_map=None, existing_logos=existing_logos
        )

        if pos is None:
            pos = (w - ow - 30, h - oh - 30)
        logo_x, logo_y = pos

        # Alpha blending
        alpha = overlay[:, :, 3] / 255.0
        roi = frame[logo_y: logo_y + oh, logo_x: logo_x + ow]
        frame[logo_y: logo_y + oh, logo_x: logo_x + ow] = overlay[:, :, :3] * alpha[
            ..., None
        ] + roi * (1 - alpha[..., None])

        # Save to temporary file and upload
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            cv2.imwrite(tmp.name, frame)

            filename = re.search(r"[^/]+$", self.img_url)
            if filename:
                filename = filename.group(0).replace(".jpg", "_share.jpg")
                with open(tmp.name, "rb") as file:
                    self.upload_to_s3(file, filename, {"ContentType": "image/jpeg"})

        new_path = "https://" + config.AWS_CUSTOMER_INCIDENTS_CLOUDFRONT_URL + "/" + filename
        return new_path