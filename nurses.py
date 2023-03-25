import simpy

class Nurse:
    '''
    Nurse class defines a nurse object with
    ID, shift schedule, and skill level
    '''

    def __init__(self, schedule_time, skill_level):
        self.env = simpy.Environment()
        self.schedule_time = schedule_time
        self.skill_level = skill_level