from talon.skia.canvas import Canvas as SkiaCanvas
from talon.skia import RoundRect
from talon.types import Rect, Point2d
from typing import TypedDict, Optional
from dataclasses import dataclass
from .ui_builder_helpers import grow_rect
from .ui_builder_screen import canvas_from_main_screen

@dataclass
class BoxModelSpacing:
    top: int = 0
    right: int = 0
    bottom: int = 0
    left: int = 0

@dataclass
class BoxModelLayout:
    margin_spacing: BoxModelSpacing
    padding_spacing: BoxModelSpacing
    margin_rect: Rect
    padding_rect: Rect
    content_rect: Rect

    def __init__(self, x: int, y: int, margin_spacing: BoxModelSpacing, padding_spacing: BoxModelSpacing):
        self.margin_spacing = margin_spacing
        self.padding_spacing = padding_spacing
        self.margin_rect = Rect(x, y, 0, 0)
        self.padding_rect = Rect(x + margin_spacing.left, y + margin_spacing.top, 0, 0)
        self.content_rect = Rect(x + margin_spacing.left + padding_spacing.left, y + margin_spacing.top + padding_spacing.top, 0, 0)

    def grow_content_rect(self, rect: Rect):
        grow_rect(self.content_rect, rect)
        self.padding_rect.width = self.content_rect.width + self.padding_spacing.left + self.padding_spacing.right
        self.padding_rect.height = self.content_rect.height + self.padding_spacing.top + self.padding_spacing.bottom
        self.margin_rect.width = self.padding_rect.width + self.margin_spacing.left + self.margin_spacing.right
        self.margin_rect.height = self.padding_rect.height + self.margin_spacing.top + self.margin_spacing.bottom


@dataclass
class Margin(BoxModelSpacing):
    pass

@dataclass
class Padding(BoxModelSpacing):
    pass

def parse_box_model(model_type: BoxModelSpacing, **kwargs) -> BoxModelSpacing:
    model = model_type()
    model_name = model_type.__name__.lower()
    model_name_x = f'{model_name}_x'
    model_name_y = f'{model_name}_y'

    if model_name in kwargs:
        all_sides_value = kwargs[model_name]
        model.top = model.right = model.bottom = model.left = all_sides_value

    if model_name_x in kwargs:
        model.left = model.right = kwargs[model_name_x]
    if model_name_y in kwargs:
        model.top = model.bottom = kwargs[model_name_y]

    for side in ['top', 'right', 'bottom', 'left']:
        side_key = f'{model_name}_{side}'
        if side_key in kwargs:
            setattr(model, side, kwargs[side_key])

    return model

class UIOptionsDict(TypedDict):
    align: str
    background_color: str
    border_color: str
    border_radius: int
    border_width: int
    bottom: int
    color: str
    flex_direction: str
    justify_content: str
    align_items: str
    height: int
    justify: str
    left: int
    margin: Margin
    padding: Padding
    right: int
    top: int
    width: int

class UITextOptionsDict(UIOptionsDict):
    size: int
    bold: bool

class UIOptions:
    align: str = "start"
    background_color: str = None
    border_color: str = "red"
    border_radius: int = 0
    border_width: int = 0
    bottom: Optional[int] = None
    top: Optional[int] = None
    left: Optional[int] = None
    right: Optional[int] = None
    color: str = "white"
    flex_direction: str = "column"
    gap: int = 16
    height: int = 0
    justify: str = "start"
    justify_content: str = "start"
    align_items: str = "start"
    margin: Margin = Margin(0, 0, 0, 0)
    padding: Padding = Padding(0, 0, 0, 0)
    width: int = 0

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.padding = parse_box_model(Padding, **{k: v for k, v in kwargs.items() if 'padding' in k})
        self.margin = parse_box_model(Margin, **{k: v for k, v in kwargs.items() if 'margin' in k})

@dataclass
class UITextOptions(UIOptions):
    size: int = 16
    bold: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Cursor:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.virtual_x = 0
        self.virtual_y = 0

    def move_to(self, x, y):
        self.x = x
        self.y = y
        self.virtual_x = x
        self.virtual_y = y

    def virtual_move_to(self, x, y):
        self.virtual_x = x
        self.virtual_y = y

    def __str__(self):
        return f"Cursor Position: ({self.x}, {self.y}, {self.virtual_x}, {self.virtual_y})"

class UIWithChildren:
    def __init__(self, options: UIOptions = None):
        self.options = options
        self.children = []

    def add_container(self, **kwargs: UIOptionsDict):
        container_options = UIOptions(**kwargs)
        container = UIContainer(container_options)
        container.cursor = Point2d(self.cursor.x, self.cursor.y)
        self.children.append(container)
        return container

    def add_text(self, text, **kwargs: UITextOptionsDict):
        text_options = UITextOptions(**kwargs)
        text = UIText(text, text_options)
        self.children.append(text)
        return text

class UIContainer(UIWithChildren):
    def __init__(self, options: UIOptions = None):
        super().__init__(options)
        self.box_model: BoxModelLayout = None

    def virtual_render(self, c: SkiaCanvas, cursor: Cursor):
        self.box_model = BoxModelLayout(cursor.virtual_x, cursor.virtual_y, self.options.margin, self.options.padding)
        cursor.virtual_move_to(self.box_model.content_rect.x, self.box_model.content_rect.y)
        for child in self.children:
            rect = child.virtual_render(c, cursor)
            if self.options.flex_direction == "column":
                cursor.virtual_move_to(cursor.virtual_x, cursor.virtual_y + rect.height + self.options.gap)
            elif self.options.flex_direction == "row":
                cursor.virtual_move_to(cursor.virtual_x + rect.width + self.options.gap, cursor.virtual_y)
            self.box_model.grow_content_rect(rect)

        return self.box_model.margin_rect

    def render(self, c: SkiaCanvas, cursor: Cursor):
        # if self.options.align_items == "center" and self.options.justify_content == "flex_end":
        #     cursor.move_to(self.box_model.content_rect.width - self.box_model.margin_rect.width - self.box_model.content_rect.width, cursor.y)
        # else:
        cursor.move_to(self.box_model.padding_rect.x, self.box_model.padding_rect.y)
        if self.options.background_color:
            c.paint.color = self.options.background_color
            if self.options.border_radius:
                c.draw_rrect(RoundRect.from_rect(self.box_model.padding_rect, x=self.options.border_radius, y=self.options.border_radius))
            else:
                c.draw_rect(self.box_model.padding_rect)
        cursor.move_to(self.box_model.content_rect.x, self.box_model.content_rect.y)

        for child in self.children:
            rect = child.render(c, cursor)
            if self.options.flex_direction == "column":
                cursor.move_to(cursor.x, cursor.y + rect.height + self.options.gap)
            elif self.options.flex_direction == "row":
                cursor.move_to(cursor.x + rect.width + self.options.gap, cursor.y)
        return self.box_model.margin_rect

class UIText:
    def __init__(self, text: str, options: UITextOptions = None):
        self.options = options
        self.text = text
        self.text_width = None
        self.text_height = None
        self.box_model = None

    def virtual_render(self, c: SkiaCanvas, cursor: Cursor):
        self.box_model = BoxModelLayout(cursor.virtual_x, cursor.virtual_y, self.options.margin, self.options.padding)
        cursor.virtual_move_to(self.box_model.content_rect.x, self.box_model.content_rect.y)
        c.paint.textsize = self.options.size
        self.text_width = c.paint.measure_text(self.text)[1].width
        self.text_height = c.paint.measure_text("E")[1].height
        self.box_model.grow_content_rect(Rect(cursor.virtual_x, cursor.virtual_y, self.text_width, self.text_height))
        return self.box_model.margin_rect

    def render(self, c: SkiaCanvas, cursor: Cursor):
        if self.options.background_color:
            c.paint.color = self.options.background_color
            if self.options.border_radius:
                c.draw_rrect(RoundRect.from_rect(self.box_model.padding_rect, x=self.options.border_radius, y=self.options.border_radius))
            else:
                c.draw_rect(self.box_model.padding_rect)
        cursor.move_to(self.box_model.content_rect.x, self.box_model.content_rect.y)
        c.paint.color = self.options.color
        c.paint.textsize = self.options.size
        c.draw_text(self.text, cursor.x, cursor.y + self.text_height)
        return self.box_model.margin_rect

class UIBuilder(UIContainer):
    def __init__(self, **options: UIOptionsDict):
        self.cursor = Cursor()
        self.canvas = None
        opts = UIOptions(**options or {})
        super().__init__(opts)

    def on_draw(self, c: SkiaCanvas):
        self.virtual_render(c, self.cursor)
        self.render(c, self.cursor)

    def show(self):
        if not self.canvas:
            self.canvas = canvas_from_main_screen()
            self.canvas.register("draw", self.on_draw)
            self.canvas.freeze()

    def hide(self):
        if self.canvas:
            self.canvas.unregister("draw", self.on_draw)
            self.canvas.hide()
            self.canvas.close()
            self.canvas = None
