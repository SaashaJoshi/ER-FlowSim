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
        self.ed_waiting_room = []
        self.medication_waiting_room = []

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
            ed_requirement = self.get_screening_results()

            if ed_requirement:
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

                    # release nurse and send to triage treatment or ed
                    self.nurse.release(nurse_request)

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

    def enter_ed_waiting_room(self, patient):
        print(f"Patient{patient.id} enters ED waiting room")
        self.ed_waiting_room.append(patient.id)
        print(f"ED waiting room: {self.ed_waiting_room}")

        ed_waiting_time = np.random.exponential(5)

        patient.waiting_time += ed_waiting_time

        # Yield triage waiting time.
        yield self.env.timeout(ed_waiting_time)

    def enter_medication_waiting_room(self, patient):
        print(f"Patient{patient.id} enters medication waiting room")
        self.medication_waiting_room.append(patient.id)
        print(f"Medication waiting room: {self.medication_waiting_room}")

        medication_waiting_time = np.random.exponential(1)

        patient.waiting_time += medication_waiting_time

        # Yield triage waiting time.
        yield self.env.timeout(medication_waiting_time)

    def give_medication(self, patient):
        # Check if medication available
        medication_availability = np.random.randint(0, 1)

        if medication_availability == 0:
            # send to waiting room
            self.env.process(self.enter_medication_waiting_room(patient))

        # Else no waiting needed; administer medication
        yield self.env.timeout(np.random.uniform(2, 2))


    def ed_treatment(self, patient):
        with self.doctor.request() as doctor_request:
            yield doctor_request

            print(f"Doctor assigned to Patient{patient.id} in ED treament")

            assessment_time = np.random.exponential(30)
            yield self.env.timeout(assessment_time)

            # Check diagnostics required (At this time subprocess not created)
            # if diagnostic_required == "Yes":
            #     pass

            # else perform procedure on patient and check if medication needed
            if self.nurse.count == self.nurse.capacity:
                # doctor gives the medication
                self.env.process(self.give_medication(patient))
            else:
                # yield nurse to give medication. but the doc is not released.
                with self.nurse.request() as nurse_request:
                    yield nurse_request

                    self.env.process(self.give_medication(patient))
                    self.nurse.release(nurse_request)

            # Refer patient to ED
            refer_immediately = np.random.randint(0, 1)

            if refer_immediately:
                self.doctor.release(doctor_request)

                # Start inpatient process/treatment
                self.env.process(self.inpatient_process(patient))
            else:
                # Wait for diagnostic results/investigation
                # IDK but the diagnosis wasn't required in earlier steps.
                # maybe re-request diagnostics here.
                pass

    def ed_process(self, patient):
        print(f"Patient{patient.id} arrives in ED")
        self.env.process(self.enter_ed_waiting_room(patient))
        self.env.process(self.ed_treatment(patient))

    def enter_inpatient_waiting_room(self, patient):
        print(f"Patient{patient.id} enters inpatient waiting room")
        self.inpatient_waiting_room.append(patient.id)
        print(f"Inpatient waiting room: {self.inpatient_waiting_room}")

        inpatient_waiting_time = np.random.exponential(1)

        patient.waiting_time += inpatient_waiting_time

        # Yield triage waiting time.
        yield self.env.timeout(inpatient_waiting_time)

    def inpatient_treatment(self, patient):
        with self.doctor.request() as doctor_request:
            yield doctor_request

            # Check patient and decide to admit
            admit = np.random.randint(0, 1)

            # release doctor
            self.doctor.release(doctor_request)

            if admit:
                # Admit patient; transfer to ward
                # Start subprocess 3
                self.env.process(self.transfer_to_ward(patient))
            else:
                # Release doctor and after waiting call senior doctor
                # check how to manage doctor skill level
                self.env.process(self.enter_ed_waiting_room())

                with self.doctor.request() as doctor_request:
                    yield doctor_request

                review_time = np.random.exponential(7)
                self.env.timeout(review_time)

                # Treatment complete; release doctor
                self.doctor.release(doctor_request)
                self.patients_processed += 1

    def inpatient_process(self, patient):
        self.env.process(self.enter_inpatient_waiting_room(patient))
        self.env.process(self.inpatient_treatment(patient))

    def transfer_to_ward(self, patient):
        # Initiates transfer process

        # Admin checks if beds available patient to bed/room
        with self.admin_staff.request() as admin_staff_request:
            yield admin_staff_request

            with self.bed.request() as bed_request:
                yield bed_request

                # Nurse transfers patient to bed/ward
                with self.nurse.request() as nurse_request:
                    yield nurse_request

                    # Release admin staff once nurse is assigned
                    self.admin_staff.release(admin_staff_request)

                    # Nurse helps transfer out of ED - ed_depart
                    ed_depart_time = np.random.uniform(20, 40)
                    self.env.timeout(ed_depart_time)

                    self.nurse.release(nurse_request)
                    self.patients_processed += 1

                    # release bed after the patient is treated
                    # then what does transfer from ED mean?
                    # aren't the beds in ED?
                    self.env.process(self.release_beds(patient))

    def release_beds(self, patient):
        yield self.env.timeout(np.random.exponential(24))

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
