import random
import numpy as np
import simpy
from patients import Patient


# from nurses import Nurse

class ERSim:
    '''
    ERSim: Emergency Room Simulation class creates objects to simulate
    an emergency room scenario
    '''

    def __init__(self, num_doctors, num_nurses, num_beds, num_admin_staff, sim_time):
        self.env = simpy.Environment()
        self.num_doctors = num_doctors
        self.num_nurses = num_nurses
        self.num_beds = num_beds
        self.sim_time = sim_time

        self.doctor = simpy.Resource(self.env, capacity=num_doctors)
        self.nurse = simpy.Resource(self.env, capacity=num_nurses)
        self.bed = simpy.Resource(self.env, capacity=num_beds)
        self.triage_waiting_room = []

        self.admin_staff = simpy.Resource(self.env, capacity=num_admin_staff)

        self.patients_processed = 0

    def run_simulation(self):
        self.env.process(self.generate_patients())
        self.env.run(until=self.sim_time)

    def generate_patients(self):
        while True:
            print(f"Patient produced")
            inter_arrival_time = random.expovariate(1 / 10)
            service_time = random.expovariate(1 / 20)
            self.env.process(self.patient_flow(Patient(id, self.env.now, service_time)))
            yield self.env.timeout(inter_arrival_time)

    def get_screening_results(self):
        return random.randint(0, 1)

    def enter_registration_counter(self):
        with self.admin_staff.request() as admin_staff_request:
            yield admin_staff_request

            registration_time = random.randint(3, 6)
            yield self.env.timeout(registration_time)

            self.admin_staff.release(admin_staff_request)

    def enter_triage_waiting_room(self, patient):
        print(f"Patient{patient.id} enters triage waiting room")
        self.triage_waiting_room.append(patient.id)
        print(f"Triage waiting room: {self.triage_waiting_room}")

        triage_waiting_time = np.random.exponential(5)

        patient.waiting_time += triage_waiting_time

        # Yield triage waiting time.
        yield self.env.timeout(triage_waiting_time)

    def get_triage_time(self, scale):
        if scale == "Screening":
            yield self.env.timeout(random.randint(5, 10))
        elif scale == "Diagnostic":
            yield self.env.timeout(random.randint(5, 10))

    def triage_process(self, patient):
        print(f"Patient{patient.id} sent to triage waiting room")
        yield self.env.process(self.enter_triage_waiting_room(patient))

        with self.nurse.request() as nurse_request:
            yield nurse_request

            # Pop patient out from triage waiting room
            self.triage_waiting_room.remove(patient.id)

            # Wait for triage service time
            yield self.env.process(self.get_triage_time("Screening"))
            print(f"Patient{patient.id} triage screening complete")

            # Requirement to be in ED or not
            ED_requirement = self.get_screening_results()

            if ED_requirement:
                print(f"Patient{patient.id} sent to registration counter")
                # send to registration desk
                self.env.process(self.enter_registration_counter())

                # Re-enters the triage process
                print(f"Patient{patient.id} in triage waiting room")
                self.env.process(self.enter_triage_waiting_room(patient))

                # Re-assign nurse
                with self.nurse.request() as nurse_request:
                    yield nurse_request

                    # Pop patient out from triage waiting room
                    self.triage_waiting_room.remove(patient.id)
                    print(f"Triage waiting room: {self.triage_waiting_room}")

                    yield self.env.process(self.get_triage_time("Diagnostic"))

                    patient.ctas_level = patient.get_ctas_level()
                    print(f"Patient{patient.id} triage diagnostic complete")
                    print(f"Patient{patient.id} CTAS level {patient.ctas_level}")

                    if patient.ctas_level == 5:
                        # Send to triage doctor
                        print(f"Patient{patient.id} CTAS V. Sent to triage doctor")
                        self.env.process(self.triage_treatment(patient))
                    else:
                        # Send to ED and start ED process
                        print(f"Patient{patient.id} sent to ED")
                        self.env.process(self.ed_process(patient))
            else:
                # Send patient to local health center
                print("Send patient to local health center")
                self.nurse.release(nurse_request)
                self.patients_processed += 1

    def triage_treatment(self, patient):
        with self.doctor.request() as doctor_request:
            yield doctor_request

            print(f"Doctor assigned to Patient{patient.id} in triage treament")

            assessment_time = np.random.exponential(30)
            yield self.env.timeout(assessment_time)

            # Not implementing the review stage for now.
            # review = patient.get_triage_treatment_review()
            # if review:
            #     print("Re-triage to higher category")
            #     patient.ctas_level = random.randint(2, 4)
            # else:

            # Treatment complete; release doctor
            self.doctor.release(doctor_request)
            self.patients_processed += 1

    def ed_process(self, patient):
        print(f"Patient{patient.id} arrives in ED")
        self.patients_processed += 1


    def patient_flow(self, patient):
        print(f"Patient{patient.id} enters the hospital")
        with self.doctor.request() as doctor_request:
            yield doctor_request

            with self.nurse.request() as nurse_request:
                yield nurse_request

                # Yield nurse for triage determination
                if patient.get_ctas_level() == 1:
                    # CTAS 1 - Send patient the other way
                    print(f"Patient{patient.id} CTAS I")
                    pass
                else:
                    # Release nurse, doctor and start triage process
                    self.nurse.release(nurse_request)
                    self.doctor.release(doctor_request)

                    print(f"Patient{patient.id} not in CTAS I")
                    print("Entering triage process")
                    yield self.env.process(self.triage_process(patient))

            # with self.doctor.request() as doctor_request:
            #     yield doctor_request
            #
            # with self.bed.request() as bed_request:
            #     yield bed_request
            #
            #     # Assign bed to patient
            #     patient.bed_assigned = bed_request
            #
            #     # Perform diagnostic tests
            #     for test in patient.tests:
            #         yield self.env.process(get_test_result(test))

            # # Wait for service time
            # yield self.env.timeout(patient.service_time)
            #
            # # Release bed and resources
            # self.bed.release(patient.bed_assigned)
            # self.nurse.release(nurse_request)
            # self.doctor.release(doctor_request)

            # self.patients_processed += 1


if __name__ == "__main__":
    sim = ERSim(3, 3, 3, 3, 40)
    sim.run_simulation()

    # Print the results
    print(f"Patients processed: {sim.patients_processed}")
