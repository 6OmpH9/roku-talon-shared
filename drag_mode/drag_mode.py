from talon import Module, Context, actions, ui, settings, ctrl, app
from talon.screen import Screen
from talon.canvas import Canvas
from talon.skia.canvas import Canvas as SkiaCanvas
from talon.types import Rect, Point2d
from itertools import islice

mod, ctx = Module(), Context()
mod.mode("drag_mode", "Drag mode. Defaults to LMB drag")
mod.tag("pan_mode", desc="Default to MMB drag")
mod.tag("roll_mode", desc="Default to RMB drag")
ctx.matches = r"""
mode: user.drag_mode
"""

canvas_grid = None
def generate_char_combo():
    ord_a = ord('a')
    ord_z = ord('z')
    colors = ["", "g", "r", "b", "p", "y"]
    excluded_chars = settings.get("user.drag_mode_exclude_chars")
    valid_chars = [chr(i) for i in range(ord_a, ord_z + 1) if chr(i) not in excluded_chars]
    for color in colors:
        for letter_one in valid_chars:
            for letter_two in valid_chars:
                yield letter_one + letter_two + color

def draw_center_text(c: SkiaCanvas, text: str, x: int, y: int):
    text_rect = c.paint.measure_text(text)[1]
    text_rect_default = c.paint.measure_text("ABC")[1]
    c.draw_text(
        text,
        x + text_rect.x - text_rect.width / 2,
        y - text_rect_default.y - text_rect_default.height / 2,
    )

grid_pos_map = {}
grid_exclude_regions = []
grid_include_regions = []

color_map = {
    "g": "00ff00",
    "r": "ff0000",
    "b": "0000ff",
    "p": "ff00ff",
    "y": "ffff00",
}
background_color_drag = "00000099"
background_color_pan = "0047AB55"
background_color_roll = "DE316355"
background_color = background_color_drag

tile_size = 60 # overwritten by settings.get("user.drag_mode_default_tile_size")

def on_grid_update(c: SkiaCanvas):
    global tile_size, grid_pos_map, background_color
    screen: Screen = ui.main_screen()
    rect = screen.rect
    offset = settings.get("user.drag_mode_offset_x_y").split(" ")
    offset_x = int(offset[0])
    offset_y = int(offset[1])
    tile_size_half = tile_size // 2
    c.paint.textsize = 16
    columns = int(rect.width // tile_size)
    rows = int(rect.height // tile_size)
    c.paint.color = "ffffff99"
    char_combo_generator = generate_char_combo()
    for y in range(rows):
        for x in range(columns):
            skip = False
            x_pos = x * tile_size + tile_size_half + offset_x
            y_pos = y * tile_size + tile_size_half + offset_y
            for region in grid_include_regions:
                if not region.contains(Point2d(x_pos, y_pos)):
                    skip = True
            for region in grid_exclude_regions:
                if region.contains(Point2d(x_pos, y_pos)):
                    skip = True
            if skip:
                continue
            text = next(char_combo_generator)
            c.paint.color = background_color
            c.draw_circle(x_pos, y_pos, 10)
            text, color = text[:2], text[2:]
            color = color_map.get(color, "ffffff")
            c.paint.color = color + "bb"
            draw_center_text(c, text, x_pos, y_pos)
            grid_pos_map[text] = Point2d(x_pos, y_pos)

def drag_mode_tile_grid_show():
    global canvas_grid, tile_size
    drag_mode_tile_grid_hide()
    screen: Screen = ui.main_screen()
    tile_size = settings.get("user.drag_mode_default_tile_size")
    canvas_grid = Canvas.from_screen(screen)
    canvas_grid.register("draw", on_grid_update)
    canvas_grid.freeze()

def drag_mode_tile_grid_hide():
    global canvas_grid, grid_pos_map
    if canvas_grid:
        canvas_grid.unregister("draw", on_grid_update)
        canvas_grid.hide()
        canvas_grid.close()
        canvas_grid = None
        grid_pos_map = {}

def get_pos_for_target(target: str) -> Point2d:
    global tile_size
    screen: Screen = ui.main_screen()
    rect = screen.rect
    tile_size_half = tile_size // 2
    columns = int(rect.width // tile_size)
    rows = int(rect.height // tile_size)
    char_combo_generator = generate_char_combo()
    for y in range(rows):
        for x in range(columns):
            text = next(char_combo_generator)
            if text == target:
                return Point2d(x * tile_size + tile_size_half, y * tile_size + tile_size_half)
    return Point2d(0, 0)

@mod.capture(rule="<user.letter> <user.letter>")
def drag_mode_target(m) -> list[str]:
    return "".join(m.letter_list)

@mod.capture(rule="<user.drag_mode_target> (to <user.drag_mode_target>)*")
def drag_mode_target_loop(m) -> list[str]:
    return m.drag_mode_target_list

def next_pos(target: str, drag: bool=False):
    pos = grid_pos_map[target]

    def callback(ev):
        if drag and ev.type == "stop":
            actions.mouse_click(button=0, up=True)

    return actions.user.mouse_move_to(pos.x, pos.y, callback_tick=callback)

def next_target(target: str, drag: bool=False):
    pos = grid_pos_map[target]
    return lambda: next_pos(target, drag)

builder = None
drag_mode_enabled = False

def drag_mode_enable():
    global drag_mode_enabled
    drag_mode_tile_grid_show()
    if not drag_mode_enabled:
        drag_mode_enabled = True
        actions.user.drag_mode_show_commands()
        actions.mode.enable("user.drag_mode")
        if settings.get("user.drag_mode_dynamic_actions_enabled"):
            actions.user.dynamic_actions_enable()
            actions.user.dynamic_actions_set_hiss("stop", actions.user.mouse_move_continuous_stop)

def drag_mode_disable():
    global drag_mode_enabled
    drag_mode_tile_grid_hide()
    if drag_mode_enabled:
        drag_mode_enabled = False
        dynamic_actions_enabled = settings.get("user.drag_mode_dynamic_actions_enabled")
        disable_dynamic_actions = settings.get("user.drag_mode_disable_dynamic_actions_on_grid_hide")
        if dynamic_actions_enabled and disable_dynamic_actions:
            actions.user.dynamic_actions_disable()
        actions.user.mouse_move_continuous_stop()
        actions.user.drag_mode_hide_commands()
        actions.mode.disable("user.drag_mode")

@mod.action_class
class Actions:
    def drag_mode_show():
        """Show the grid"""
        global background_color
        background_color = background_color_drag
        drag_mode_enable()
        ctx.tags = []

    def pan_mode_show():
        """Show the grid"""
        global background_color
        background_color = background_color_pan
        drag_mode_enable()
        ctx.tags = ["user.pan_mode"]

    def roll_mode_show():
        """Show the grid"""
        global background_color
        background_color = background_color_roll
        drag_mode_enable()
        ctx.tags = ["user.roll_mode"]

    def drag_mode_hide():
        """Hide the grid"""
        drag_mode_disable()

    def drag_mode_move_mouse(target: str):
        """Move the mouse to the grid position"""
        pos = grid_pos_map[target]
        actions.mouse_move(pos.x, pos.y)
        actions.user.mouse_move_continuous_stop()

    def drag_mode_move_mouse_to_target(target: str):
        """Move the mouse to the grid position"""
        pos = grid_pos_map[target]
        actions.user.mouse_move_to(pos.x, pos.y)

    def drag_mode_fly_towards(target: str):
        """Move the mouse to the grid position"""
        pos = grid_pos_map[target]
        actions.user.mouse_move_continuous_towards(pos.x, pos.y)

    def drag_mode_more_squares():
        """Increase the number of squares"""
        global tile_size
        tile_size += settings.get("user.drag_mode_tile_increment_size")
        if canvas_grid:
            canvas_grid.freeze()

    def drag_mode_less_squares():
        """Decrease the number of squares"""
        global tile_size
        tile_size -= settings.get("user.drag_mode_tile_increment_size")
        if canvas_grid:
            canvas_grid.freeze()


    def drag_mode_move_to_target_loop(targets: list[list[str]]):
        """Move the mouse to the grid position"""
        actual_targets = targets[0]
        pos = grid_pos_map[actual_targets[0]]
        actions.user.mouse_move_to(pos.x, pos.y)
        for target in islice(actual_targets, 1, None):
            actions.user.mouse_move_queue(next_target(target))

    # def drag_mode_drag_to_target_loop(targets: list[list[str]], button: int = 0):
    #     """Move the mouse to the grid position"""
    #     actual_targets = targets[0]
    #     pos = grid_pos_map[actual_targets[0]]
    #     actions.user.mouse_move_to(pos.x, pos.y, callback_tick=lambda ev: ctrl.mouse_click(button=button, down=True) if ev.type == "stop" else None)
    #     for i, target in enumerate(islice(actual_targets, 1, None)):
    #         if i == len(actual_targets) - 1:
    #             actions.user.mouse_move_queue(next_target(target, True))
    #         else:
    #             actions.user.mouse_move_queue(next_target(target))

    def drag_mode_drag_and_drop(target_one: str, target_two: str, button: int = 0):
        """Drag and drop from target one to target two"""
        start_pos = grid_pos_map[target_one]
        target_pos = grid_pos_map[target_two]

        def release():
            ctrl.mouse_click(button=button, up=True)

        def moved():
            ctrl.mouse_click(button=button, down=True)
            actions.user.mouse_move_from_to(start_pos.x, start_pos.y, target_pos.x, target_pos.y, 200, callback_stop=release)

        actions.user.mouse_move_to(start_pos.x, start_pos.y, 200, callback_stop=moved)

    def drag_mode_bring_to_center(target: str, button: int = 0):
        """Center the target"""
        rect = ui.active_window().rect
        end_pos_x = rect.left + (rect.width / 2)
        end_pos_y = rect.top + (rect.height / 2)
        start_pos = grid_pos_map[target]
        def release():
            ctrl.mouse_click(button=button, up=True)

        def moved():
            ctrl.mouse_click(button=button, down=True)
            actions.user.mouse_move_from_to(start_pos.x, start_pos.y, end_pos_x, end_pos_y, 200, callback_stop=release)

        actions.user.mouse_move_to(start_pos.x, start_pos.y, 200, callback_stop=moved)

    def drag_mode_exclude_area_targets(target_one: str, target_two: str):
        """Exclude the grid of numbers from target one to target two"""
        global grid_exclude_regions
        if canvas_grid:
            pos_one = grid_pos_map[target_one]
            pos_two = grid_pos_map[target_two]
            grid_exclude_regions.append(Rect(pos_one.x, pos_one.y, pos_two.x - pos_one.x + 1, pos_two.y - pos_one.y + 1))
            canvas_grid.freeze()

    def drag_mode_isolate_area_targets(target_one: str, target_two: str):
        """Isolate the grid of numbers from target one to target two"""
        global grid_include_regions
        if canvas_grid:
            pos_one = grid_pos_map[target_one]
            pos_two = grid_pos_map[target_two]
            grid_include_regions.append(Rect(pos_one.x, pos_one.y, pos_two.x - pos_one.x + 1, pos_two.y - pos_one.y + 1))
            canvas_grid.freeze()

    def drag_mode_exclude_area_rect(x: int, y: int, width: int, height: int):
        """Exclude the grid of numbers with a rectangle"""
        global grid_exclude_regions
        grid_exclude_regions.append(Rect(x, y, width, height))
        if canvas_grid:
            canvas_grid.freeze()

    def drag_mode_exclude_line(target_one: str, target_two: str = None):
        """Exclude the grid of numbers with a line"""
        global grid_exclude_regions
        if canvas_grid:
            pos_one = grid_pos_map[target_one]
            pos_two = grid_pos_map[target_two] if target_two else grid_pos_map[target_one]
            grid_exclude_regions.append(Rect(0, pos_one.y, 1920, pos_two.y - pos_one.y + 1))
            canvas_grid.freeze()

    def drag_mode_bring(target: str, button: int = 0):
        """Bring the target to current mouse position"""
        (x, y) = ctrl.mouse_pos()
        target_pos = grid_pos_map[target]
        # actions.user.drag_mode_move_mouse(target)
        def release(ev):
            if ev.type == "stop":
                ctrl.mouse_click(button=button, up=True)

        def moved(ev):
            if ev.type == "stop":
                ctrl.mouse_click(button=button, down=True)
                actions.user.mouse_move_from_to(target_pos.x, target_pos.y, x, y, 200, callback_tick=release)

        actions.user.mouse_move_to(target_pos.x, target_pos.y, 200, callback_tick=moved)

    def drag_mode_bring_to(target: str, button: int = 0):
        """Bring the target to current mouse position"""
        (x, y) = ctrl.mouse_pos()
        target_pos = grid_pos_map[target]
        def release(ev):
            if ev.type == "stop":
                ctrl.mouse_click(button=button, up=True)

        ctrl.mouse_click(button=button, down=True)
        actions.user.mouse_move_from_to(x, y, target_pos.x, target_pos.y, callback_tick=release)


    def drag_mode_reset():
        """Reset the grid"""
        global grid_exclude_regions, grid_include_regions, tile_size
        tile_size = settings.get("user.drag_mode_default_tile_size")
        grid_exclude_regions = []
        grid_include_regions = []
        actions.user.mouse_move_continuous_stop()
        if canvas_grid:
            canvas_grid.freeze()

    def drag_mode_stop():
        """Reset the grid"""
        actions.user.mouse_move_continuous_stop()

    def drag_mode_show_commands():
        """Show the grid commands"""
        global builder

        (screen, div, text) = actions.user.ui_elements(["screen", "div", "text"])

        container_css = {
            "background_color": "222222",
            "margin_right": 32,
            "padding": 16,
            "flex_direction": "column",
            "justify_content": "center",
            "align_items": "center",
            "border_width": 1,
            "border_color": "666666",
            "border_radius": 4,
        }

        builder = screen(justify_content="center", align_items="flex_end")[
            div(container_css)[
                div(flex_direction="column", gap=12)[
                    text("Mode:", color="87CEEB", font_weight="bold"),
                    text("drag mode - LMB"),
                    text("roll mode - RMB"),
                    text("pan mode - MMB"),
                    text("Commands:", color="87CEEB", font_weight="bold", margin_top=12),
                    text("<T>"),
                    text("<T> to <T>"),
                    text("go <T>"),
                    text("fly <T>"),
                    text("fly <dir>"),
                    text("fly stop"),
                    text("<T> <dir>"),
                    text("halt / stop"),
                    text("bring <T>"),
                    text("bring this to <T>"),
                    text("center <T>"),
                    text("tick <dir>"),
                    text("gear up"),
                    text("gear down"),
                    text("Noises:", color="87CEEB", font_weight="bold", margin_top=12),
                    text("hiss: stop"),
                    text("Layout:", color="87CEEB", font_weight="bold", margin_top=12),
                    text("more squares"),
                    text("less squares"),
                    text("clear <T> past <T>"),
                    text("clear line <T>"),
                    text("take <T> past <T>"),
                    text("grid reset"),
                    text("grid hide", color="F33A6A", font_weight="bold", margin_top=12),
                ]
            ]
        ]

        builder.show()

    def drag_mode_hide_commands():
        """Hide the grid commands"""
        global builder
        if builder:
            builder.hide()
            builder = None