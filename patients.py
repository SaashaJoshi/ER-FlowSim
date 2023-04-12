import random
import simpy

class Patient:
    '''
    Patient class defines a patient object with
    arrival time, service time, CTAS level, and assigned bed number
    '''

    patient_count = 0

    def __init__(self, arrival_time, leave_time=0, ctas_level=None, bed_assigned=None):
        self.env = simpy.Environment()

        Patient.patient_count += 1
        self.id = Patient.patient_count
        self.arrival_time = arrival_time
        self.triage_waiting_time = 0
        self.ed_waiting_time = 0
        self.medication_waiting_time = 0
        self.inpatient_waiting_time = 0
        self.leave_time = leave_time
        self.ctas_level = ctas_level
        self.tests = []
        self.bed_assigned = bed_assigned

    def get_ctas_level(self):
        if self.ctas_level >0:
            return self.ctas_level
        else:
            return int(random.randint(1, 5))

    def get_triage_treatment_review(self):
        return random.randint(0, 1)