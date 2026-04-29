"""
Image handling utilities for terminal display.

Provides image processing, resizing, and ASCII art rendering.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from PIL.Image import Image

from exceptions import CopilotError


class ImageError(CopilotError):
    """Image operation error."""

    pass


@dataclass
class ImageSize:
    """Image dimensions."""

    width: int
    height: int

    def scale_to_fit(
        self, max_width: int, max_height: int
    ) -> "ImageSize":
        """
        Scale image to fit within max dimensions while maintaining aspect ratio.

        Args:
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels

        Returns:
            New scaled dimensions
        """
        aspect_ratio = self.width / self.height

        if self.width > max_width:
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            new_width = self.width
            new_height = self.height

        if new_height > max_height:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)

        return ImageSize(new_width, new_height)


class ImageProcessor:
    """Processes images for terminal display."""

    # ASCII characters for rendering (from dark to light)
    ASCII_CHARS = "@%#*+=-:. "

    def __init__(self) -> None:
        """Initialize image processor."""
        self._has_pillow = self._check_pillow()

    @staticmethod
    def _check_pillow() -> bool:
        """Check if Pillow is available."""
        try:
            from PIL import Image
            return True
        except ImportError:
            return False

    def load_image(self, path: str) -> Optional["Image.Image"]:
        """
        Load an image from file.

        Args:
            path: Path to image file

        Returns:
            PIL Image object, or None if image cannot be loaded

        Raises:
            ImageError: If Pillow is not installed
        """
        if not self._has_pillow:
            raise ImageError(
                "Pillow (PIL) is required for image handling. "
                "Install with: pip install Pillow"
            )

        try:
            from PIL import Image
            image = Image.open(path)
            return image
        except Exception as e:
            raise ImageError(
                f"Failed to load image from {path}",
                details=str(e),
            )

    def resize_image(
        self,
        image: "Image.Image",
        width: int,
        height: int,
    ) -> "Image.Image":
        """
        Resize image to specified dimensions.

        Args:
            image: PIL Image object
            width: Target width
            height: Target height

        Returns:
            Resized PIL Image object
        """
        try:
            from PIL import Image
            return image.resize((width, height), Image.Resampling.LANCZOS)
        except Exception as e:
            raise ImageError(
                f"Failed to resize image to {width}x{height}",
                details=str(e),
            )

    def convert_to_ascii(
        self,
        image: "Image.Image",
        width: int = 100,
    ) -> str:
        """
        Convert image to ASCII art.

        Args:
            image: PIL Image object
            width: Width in ASCII characters

        Returns:
            ASCII art string
        """
        try:
            from PIL import Image

            # Calculate height maintaining aspect ratio
            aspect_ratio = image.height / image.width
            height = int(width * aspect_ratio * 0.55)  # 0.55 for character aspect

            # Resize and convert to grayscale
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            image = image.convert("L")

            # Get pixel data
            pixels = image.getdata()

            # Map pixels to ASCII
            ascii_str = ""
            for i, pixel in enumerate(pixels):
                char_index = int((pixel / 255) * (len(self.ASCII_CHARS) - 1))
                ascii_str += self.ASCII_CHARS[char_index]
                if (i + 1) % width == 0:
                    ascii_str += "\n"

            return ascii_str
        except Exception as e:
            raise ImageError(
                "Failed to convert image to ASCII art",
                details=str(e),
            )

    def get_image_size(self, path: str) -> ImageSize:
        """
        Get image dimensions.

        Args:
            path: Path to image file

        Returns:
            ImageSize with width and height

        Raises:
            ImageError: If image cannot be loaded
        """
        image = self.load_image(path)
        return ImageSize(image.width, image.height)

    def optimize_for_terminal(
        self,
        path: str,
        max_width: int = 100,
        max_height: int = 50,
    ) -> str:
        """
        Load and optimize image for terminal display.

        Args:
            path: Path to image file
            max_width: Maximum width in ASCII characters
            max_height: Maximum height in lines

        Returns:
            ASCII art string optimized for terminal

        Raises:
            ImageError: If image cannot be processed
        """
        try:
            image = self.load_image(path)
            ascii_art = self.convert_to_ascii(image, max_width)

            # Trim to max height
            lines = ascii_art.split("\n")
            if len(lines) > max_height:
                lines = lines[:max_height]

            return "\n".join(lines)
        except Exception as e:
            raise ImageError(
                "Failed to optimize image for terminal",
                details=str(e),
            )


class ImageCache:
    """Simple cache for processed images."""

    def __init__(self, max_size: int = 10) -> None:
        """
        Initialize image cache.

        Args:
            max_size: Maximum number of images to cache
        """
        self.max_size = max_size
        self._cache: dict = {}

    def get(self, key: str) -> str | None:
        """Get cached ASCII art."""
        return self._cache.get(key)

    def set(self, key: str, value: str) -> None:
        """Store ASCII art in cache."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()


# Global instances
_image_processor: ImageProcessor | None = None
_image_cache: ImageCache | None = None


def get_image_processor() -> ImageProcessor:
    """Get or create global image processor."""
    global _image_processor
    if _image_processor is None:
        _image_processor = ImageProcessor()
    return _image_processor


def get_image_cache() -> ImageCache:
    """Get or create global image cache."""
    global _image_cache
    if _image_cache is None:
        _image_cache = ImageCache()
    return _image_cache
