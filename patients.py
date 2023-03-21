import random
import simpy

class Patient:
    '''
    Patient class defines a patient object with
    arrival time, service time, CTAS level, and assigned bed number
    '''

    patient_count = 0

    def __init__(self, id, arrival_time, service_time, waiting_time=0, ctas_level=None, tests=None, bed_assigned=None):
        self.env = simpy.Environment()

        Patient.patient_count += 1
        self.id = Patient.patient_count

        self.arrival_time = arrival_time
        self.service_time = service_time
        self.waiting_time = waiting_time

        self.ctas_level = ctas_level
        self.tests = tests
        self.bed_assigned = bed_assigned

    def get_ctas_level(self):
        return random.randint(1, 5)

    def get_triage_treatment_review(self):
        return random.randint(0, 1)

    def get_test_result(self, test):
        if test == 'MRI':
            yield simpy.Timeout(self.env, 45)
        elif test == 'XRay':
            yield simpy.Timeout(self.env, 15)
        elif test == 'CT':
            yield simpy.Timeout(self.env, 30)
