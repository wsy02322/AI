from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class CatalogTests(unittest.TestCase):
    def test_openai_size_and_public_count(self) -> None:
        from app.catalog import MODELS, get_model, openai_size

        self.assertEqual(len(MODELS), 8)
        self.assertEqual(openai_size("1:1"), "1024x1024")
        self.assertEqual(openai_size("16:9"), "1536x1024")
        self.assertEqual(get_model("openai:gpt-image-2")["edit"], "mask")
        from app.catalog import MASK_MODEL_ID
        self.assertEqual(MASK_MODEL_ID, "openai:gpt-image-2")
        self.assertEqual(get_model("google:gemini-3-pro-image")["edit"], "semantic")
        with self.assertRaises(KeyError):
            get_model("nope")


class MaskTests(unittest.TestCase):
    def test_white_paint_becomes_transparent(self) -> None:
        from app.providers import normalize_openai_mask

        canvas = io.BytesIO()
        Image.new("RGBA", (4, 4), (10, 20, 30, 255)).save(canvas, format="PNG")
        mask = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        mask.putpixel((1, 1), (255, 255, 255, 200))
        mask_buf = io.BytesIO()
        mask.save(mask_buf, format="PNG")
        out = Image.open(io.BytesIO(normalize_openai_mask(mask_buf.getvalue(), canvas.getvalue())))
        self.assertEqual(out.size, (4, 4))
        self.assertEqual(out.getpixel((1, 1))[3], 0)
        self.assertEqual(out.getpixel((0, 0))[3], 255)


class StoreTests(unittest.TestCase):
    def test_version_roundtrip(self) -> None:
        from app import config, store

        tmp = Path(tempfile.mkdtemp(prefix="studio-store-"))
        old = config.DATA_DIR
        config.DATA_DIR = tmp
        try:
            work = store.create_work("u1", "t")
            png = Image.new("RGB", (2, 2), (1, 2, 3))
            buf = io.BytesIO()
            png.save(buf, format="PNG")
            work = store.add_version(
                "u1",
                work["id"],
                image_bytes=buf.getvalue(),
                prompt="p",
                model="openai:gpt-image-2",
                kind="generate",
            )
            self.assertEqual(len(work["versions"]), 1)
            self.assertTrue(store.file_path("u1", work["id"], work["versions"][0]["file"]))
            self.assertIsNone(store.file_path("u1", work["id"], "../secret.png"))
        finally:
            config.DATA_DIR = old


if __name__ == "__main__":
    unittest.main()
