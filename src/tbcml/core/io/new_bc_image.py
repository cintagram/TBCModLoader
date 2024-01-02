from typing import Optional

from PIL import Image, ImageDraw

try:
    from PyQt5.QtGui import QImage, QIcon, QPixmap
except ImportError:
    pass

from tbcml import core

from marshmallow_dataclass import dataclass


@dataclass
class NewBCImage:
    b64: str = ""

    def __post_init__(self):
        self.__image: Optional[Image.Image] = None
        self._qimg: Optional["QImage"] = None
        self.__original_data = core.Data.from_base_64(self.b64)
        self.__original_img: Optional[Image.Image] = None

    def save_b64(self):
        self.to_data()

    @property
    def image(self) -> Image.Image:
        if not self.__image:
            if not self.b64:
                self.__image = Image.new("RGBA", (1, 1))
            else:
                self.__image = Image.open(
                    core.Data.from_base_64(self.b64).to_bytes_io()
                )
            self.__original_img = self.__image.copy()
            self.__original_data = core.Data.from_base_64(self.b64)
        if self.__original_img is None:
            self.__original_img = self.__image.copy()
        return self.__image

    def copy(self):
        data = self.to_data()
        return NewBCImage(data.to_base_64())

    @staticmethod
    def create_empty():
        return NewBCImage()

    def is_empty(self):
        return not self.b64

    @property
    def width(self):
        return self.image.width

    @property
    def height(self):
        return self.image.height

    @staticmethod
    def from_size(width: int, height: int):
        image = Image.new("RGBA", (width, height))
        image_data = core.Data()
        bytes_io = image_data.to_bytes_io()
        image.save(bytes_io, format="PNG")
        return NewBCImage(core.Data(bytes_io.getvalue()).to_base_64())

    def crop_rect(self, x1: int, y1: int, x2: int, y2: int) -> "NewBCImage":
        dt = self.image.crop((x1, y1, x2, y2))
        image_data = core.Data()
        bytes_io = image_data.to_bytes_io()
        dt.save(bytes_io, format="PNG")
        return NewBCImage(core.Data(bytes_io.getvalue()).to_base_64())

    def get_subimage(self, rect: "core.Rect") -> "NewBCImage":
        return self.crop_rect(rect.x, rect.y, rect.x + rect.width, rect.y + rect.height)

    def scale_x(self, scale: float):
        if scale < 0:
            self.flip_x()
            scale *= -1
        self.__image = self.image.resize(
            (int(self.width * scale), self.height), resample=Image.BICUBIC
        )

    def scale_y(self, scale: float):
        if scale < 0:
            self.flip_y()
            scale *= -1
        self.__image = self.image.resize(
            (self.width, int(self.height * scale)), resample=Image.BICUBIC
        )

    def scale(self, scale_x: float, scale_y: float):
        self.scale_x(scale_x)
        self.scale_y(scale_y)

    def flip_x(self):
        self.__image = self.image.transpose(Image.FLIP_LEFT_RIGHT)

    def flip_y(self):
        self.__image = self.image.transpose(Image.FLIP_TOP_BOTTOM)

    def add_image(self, image: "NewBCImage", x: int, y: int):
        self.image.paste(image.image, (x, y), image.image)

    def save(self, path: "core.Path"):
        self.image.save(path.to_str(), format="PNG")

    def to_data(self):
        if self.image.tobytes() == self.__original_img.tobytes() and len(self.b64) > 0:  # type: ignore
            return self.__original_data
        bytes_io = core.Data().to_bytes_io()
        self.image.save(bytes_io, format="PNG")
        data = core.Data(bytes_io.getvalue())
        self.b64 = data.to_base_64()
        return data

    @staticmethod
    def from_base_64(base_64: str) -> "NewBCImage":
        return NewBCImage(base_64)

    def to_base_64(self) -> str:
        return self.to_data().to_base_64()

    def paste(self, image: "NewBCImage", x: int, y: int):
        self.image.paste(image.image, (x, y), image.image)

    def convert_to_rgba(self):
        self.__image = self.image.convert("RGBA")

    def paste_rect(self, image: "NewBCImage", rect: "core.Rect"):
        self.image.paste(
            image.image,
            (rect.x, rect.y, rect.x + rect.width, rect.y + rect.height),
            image.image,
        )

    def putpixel(self, x: int, y: int, color: tuple[int, int, int, int]):
        self.image.putpixel((x, y), color)

    def fix_libpng_warning(self):
        """Fixes the libpng warning: iCCP: known incorrect sRGB profile"""

        if "icc_profile" in self.image.info:
            del self.image.info["icc_profile"]

        return self

    def to_qimage(self) -> "QImage":
        if self._qimg:
            return self._qimg
        self._qimg = QImage.fromData(self.to_data().to_bytes())
        return self._qimg

    def to_qicon(self) -> "QIcon":
        return QIcon(QPixmap.fromImage(self.to_qimage()))

    def force_q_refresh(self):
        self._qimg = None

    def force_refresh(self):
        self.__image = None
        self.force_q_refresh()

    def crop_circle(self):
        if self.width != self.height:
            raise ValueError("Image must be square")
        mask = Image.new("L", self.image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, self.width, self.height), fill=255)
        self.image.putalpha(mask)