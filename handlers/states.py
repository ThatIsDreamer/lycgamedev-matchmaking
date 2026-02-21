from aiogram.fsm.state import State, StatesGroup


class SoloForm(StatesGroup):
    display_name = State()
    age_category = State()
    participation_format = State()
    specialty = State()
    description = State()


class TeamForm(StatesGroup):
    team_name = State()
    pitch_format = State()
    description = State()
    roles = State()
