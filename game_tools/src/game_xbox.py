from talon import actions, Module, cron, settings
from typing import Union, Any, Optional
from dataclasses import dataclass
from .game_core import event_subscribers

mod = Module()
mod.setting(
    "game_xbox_button_hold",
    type=int,
    default=50,
    desc="The amount of time to hold a button before releasing it."
)

gear_values = {
    "left_stick": ".2 .4 .6 .8 1",
    "right_stick": ".3 .55 .65 .73 .85",
    "left_trigger": ".2 .4 .6 .8 1",
    "right_trigger": ".2 .4 .6 .8 1",
}

def get_gear_values(subject: str, gear: str = 5):
    try:
        return float(gear_values[subject].split(" ")[gear - 1])
    except KeyError:
        return 1

class GearState:
    gear: int
    value: float

    def __init__(self, subject: str, gear: Union[int, str]):
        self.gear = int(gear)
        self.value = get_gear_values(subject, gear)

    def set_gear(self, gear: Union[int, str]):
        self.gear = int(gear)
        self.value = get_gear_values(gear)

button_event_subscribers = []
dpad_hold_dir = None
left_stick_dir = (0, 0)
right_stick_dir = (0, 0)
gear_state = {
    "left_stick": GearState("left_stick", 5),
    "right_stick": GearState("right_stick", 3),
    "left_trigger": GearState("left_trigger", 5),
    "right_trigger": GearState("right_trigger", 5),
}
held_buttons = set()
button_up_pending_jobs = {}
button_hold_time = 50
# button_hold_time = settings.get("user.game_xbox_button_hold")

@dataclass
class GameXboxEvent:
    subject: str # specific button or left_stick, right_stick, left_trigger, right_trigger
    type: str
    value: Optional[Any]

EVENT_TYPE_HOLD = "hold"
EVENT_TYPE_RELEASE = "release"
EVENT_TYPE_DIR_CHANGE = "dir_change"
EVENT_TYPE_GEAR_CHANGE = "gear_change"

LEFT_STICK = "left_stick"
RIGHT_STICK = "right_stick"
LEFT_TRIGGER = "left_trigger"
RIGHT_TRIGGER = "right_trigger"

dir_to_xy = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}

xbox_trigger_map = {
    "lt": LEFT_TRIGGER,
    "rt": RIGHT_TRIGGER,
    "l2": LEFT_TRIGGER,
    "r2": RIGHT_TRIGGER,
    "left_trigger": LEFT_TRIGGER,
    "right_trigger": RIGHT_TRIGGER,
}

xbox_button_map = {
    "a": "a",
    "b": "b",
    "x": "x",
    "y": "y",
    "dpad_up": "dpad_up",
    "dpad_down": "dpad_down",
    "dpad_left": "dpad_left",
    "dpad_right": "dpad_right",
    "lb": "left_shoulder",
    "rb": "right_shoulder",
    "l1": "left_shoulder",
    "r1": "right_shoulder",
    "l3": "left_thumb",
    "r3": "right_thumb",
    "left_shoulder": "left_shoulder",
    "right_shoulder": "right_shoulder",
    "left_thumb": "left_thumb",
    "right_thumb": "right_thumb",
    "start": "start",
    "back": "back",
    "guide": "guide",
    **xbox_trigger_map,
}

def xbox_left_analog_hold_dir(dir: str, power: float = None):
    """Hold a left analog direction"""
    global left_stick_dir
    power = power or gear_state["left_stick"].value
    xy_dir = dir_to_xy[dir]
    actions.user.vgamepad_left_stick(xy_dir[0] * power, xy_dir[1] * power)
    if left_stick_dir != xy_dir:
        event_trigger(LEFT_STICK, EVENT_TYPE_DIR_CHANGE, xy_dir)
    left_stick_dir = xy_dir

def xbox_right_analog_hold_dir(dir: str, power: float = None):
    """Hold a right analog direction"""
    global right_stick_dir
    power = power or gear_state["right_stick"].value
    xy_dir = dir_to_xy[dir]
    actions.user.vgamepad_right_stick(xy_dir[0] * power, xy_dir[1] * power)
    if right_stick_dir != xy_dir:
        event_trigger(RIGHT_STICK, EVENT_TYPE_DIR_CHANGE, xy_dir)
    right_stick_dir = xy_dir

def xbox_dpad_hold_dir(dir: str):
    """Hold a dpad direction"""
    global dpad_hold_dir
    actions.user.vgamepad_dpad_dir_hold(dir)
    if dpad_hold_dir != dir:
        event_trigger("dpad", EVENT_TYPE_DIR_CHANGE, dir)
    dpad_hold_dir = dir

def xbox_set_gear(subject: str, gear: Union[str, int]):
    gear_state[subject].set_gear(gear)
    event_trigger(subject, EVENT_TYPE_GEAR_CHANGE, gear_state[subject])

def xbox_button_press(button: str, hold: int = None):
    global button_hold_time
    hold = hold or button_hold_time
    xbox_button_hold(button, hold)

def xbox_button_hold(button: str, hold: int = None):
    global button_up_pending_jobs, held_buttons
    button = xbox_button_map[button]
    if button in [LEFT_TRIGGER, RIGHT_TRIGGER]:
        xbox_trigger_hold(button, hold=hold)
        return

    if button_up_pending_jobs.get(button):
        cron.cancel(button_up_pending_jobs[button])
    held_buttons.add(button)
    actions.user.vgamepad_button_hold(button)
    event_trigger(button, EVENT_TYPE_HOLD)

    print("button hold", button, hold)
    if hold:
        button_up_pending_jobs[button] = cron.after(f"{hold}ms", lambda: xbox_button_release(button))

def xbox_button_release(button: str):
    global button_up_pending_jobs
    button = xbox_button_map[button]
    if button in [LEFT_TRIGGER, RIGHT_TRIGGER]:
        xbox_trigger_release(button)
        return

    actions.user.vgamepad_button_release(button)
    event_trigger(button, EVENT_TYPE_RELEASE)
    button_up_pending_jobs[button] = None
    if button in held_buttons:
        held_buttons.remove(button)

def xbox_button_toggle(button: str):
    button = xbox_button_map[button]
    if button in held_buttons:
        xbox_button_release(button)
    else:
        xbox_button_hold(button)

def xbox_left_stick(x: float, y: float):
    global left_stick_dir
    actions.user.vgamepad_left_stick(x, y)
    if left_stick_dir != (x, y):
        event_trigger(LEFT_STICK, EVENT_TYPE_DIR_CHANGE, (x, y))
    left_stick_dir = (x, y)

def xbox_right_stick(x: float, y: float):
    global right_stick_dir
    actions.user.vgamepad_right_stick(x, y)
    if right_stick_dir != (x, y):
        event_trigger(RIGHT_STICK, EVENT_TYPE_DIR_CHANGE, (x, y))
    right_stick_dir = (x, y)

def xbox_trigger_hold(button: str, power: float = None, hold: int = None):
    global button_up_pending_jobs, held_buttons
    power = power or gear_state[button].value
    if button_up_pending_jobs.get(button):
        cron.cancel(button_up_pending_jobs[button])
    held_buttons.add(button)
    actions.user.vgamepad_left_trigger(power)
    event_trigger(button, EVENT_TYPE_HOLD, gear_state[button])

    if hold:
        button_up_pending_jobs[button] = cron.after(f"{hold}ms", lambda: xbox_trigger_release(button))

def xbox_trigger_release(button):
    global button_up_pending_jobs
    getattr(actions.user, f"vgamepad_{button}")(0)
    event_trigger(button, EVENT_TYPE_RELEASE)
    button_up_pending_jobs[button] = None
    if button in held_buttons:
        held_buttons.remove(button)

def xbox_stop_all():
    xbox_left_stick(0, 0)
    xbox_right_stick(0, 0)
    for button in held_buttons:
        actions.user.vgamepad_button_release(button)
    held_buttons.clear()

def xbox_stopper():
    """Perform general purpose stopper based on priority"""
    if right_stick_dir != (0, 0):
        xbox_right_stick(0, 0)
        return

    xbox_left_stick(0, 0)
    for button in held_buttons:
        xbox_button_release(button)
    held_buttons.clear()

def event_register(callback: callable):
    global event_subscribers
    if "on_xbox" not in event_subscribers:
        event_subscribers["on_xbox"] = []
    event_subscribers["on_xbox"].append(callback)

def event_unregister(callback: callable):
    global event_subscribers
    if "on_xbox" in event_subscribers:
        event_subscribers["on_xbox"].remove(callback)
        if not event_subscribers["on_xbox"]:
            del event_subscribers["on_xbox"]

def event_trigger(subject: str, type: str, value: Any = None):
    """
    Subject: the specific button or left_stick, right_stick, left_trigger, right_trigger
    Event type: hold, release, dir_change, gear_change
    Value: Optional value for the event
    """
    global event_subscribers
    print("a triggering event", subject, type, value)
    print(event_subscribers)
    if "on_xbox" in event_subscribers:
        for callback in event_subscribers["on_xbox"]:
            callback(GameXboxEvent(subject, type, value))

# def on_xbox_gamepad_enable():
#     global button_hold_time
#     button_hold_time = settings.get("user.game_xbox_button_hold")

@mod.action_class
class Actions:
    def game_event_register_on_xbox_gamepad_event(callback: callable):
        """
        ```
        def on_gamepad_event(event: Any):
            print(event.subject, event.type, event.value)

        actions.user.game_event_register_on_xbox_gamepad_event(on_gamepad_event)
        ```
        """
        event_register(callback)

    def game_event_unregister_on_xbox_gamepad_event(callback: callable):
        """
        Unregister a callback for a specific game event.
        """
        event_unregister(callback)