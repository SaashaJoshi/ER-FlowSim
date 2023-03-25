import random
import numpy as np
import simpy
from patients import Patient


class ERSim:
    '''
    ERSim: Emergency Room Simulation class creates objects to simulate
    an emergency room scenario
    '''

    patient_count = 0

    def __init__(self, num_doctors, num_nurses, num_beds, num_admin_staff, sim_time):
        self.env = simpy.Environment()
        self.num_doctors = num_doctors
        self.num_nurses = num_nurses
        self.num_beds = num_beds
        self.sim_time = sim_time

        self.patients = []
        self.doctor = simpy.Resource(self.env, capacity=num_doctors)
        self.nurse = simpy.Resource(self.env, capacity=num_nurses)
        self.admin_staff = simpy.Resource(self.env, capacity=num_admin_staff)

        self.bed = simpy.Resource(self.env, capacity=num_beds)
        self.ecg_machine = simpy.Resource(self.env, capacity=2)
        self.ct_machine = simpy.Resource(self.env, capacity=2)
        self.x_ray_machine = simpy.Resource(self.env, capacity=4)

        self.triage_waiting_room = []
        self.ed_waiting_room = []
        self.medication_waiting_room = []

        self.medication = simpy.Container(self.env, init=0)
        self.blood_tubes = simpy.Container(self.env, capacity=30)
        self.stationary = simpy.Container(self.env, capacity=30)
        self.patients_processed = 0

    def run_simulation(self):
        self.env.process(self.generate_patients())
        self.env.run(until=self.sim_time)

    def generate_patients(self):
        while True:
            print(f"Patient produced")
            inter_arrival_time = random.expovariate(1 / 6)
            service_time = random.expovariate(1)
            ERSim.patient_count += 1
            patient = Patient(self.env.now, service_time)
            self.patients.append(patient)
            self.env.process(self.patient_flow(patient))
            yield self.env.timeout(inter_arrival_time)

    def get_screening_results(self):
        return random.choices([0, 1], weights=[9, 1])

    def enter_registration_counter(self):
        with self.admin_staff.request() as admin_staff_request:
            yield admin_staff_request

            registration_time = random.randint(0, 1)
            yield self.env.timeout(registration_time)

            self.admin_staff.release(admin_staff_request)

    def enter_triage_waiting_room(self, patient):
        print(f"Patient{patient.id} enters triage waiting room")
        self.triage_waiting_room.append(patient.id)
        print(f"Triage waiting room: {self.triage_waiting_room}")

        triage_waiting_time = np.random.exponential(1)

        patient.waiting_time += triage_waiting_time

        # Yield triage waiting time.
        yield self.env.timeout(triage_waiting_time)

    def get_triage_time(self, scale):
        if scale == "Screening":
            yield self.env.timeout(random.randint(5, 10))
        elif scale == "Diagnostic":
            yield self.env.timeout(random.randint(5, 10))

    def get_urine_test(self, patient):
        print(f"Patient{patient.id} arrives for urine test")
        with self.nurse.request() as nurse_request:
            yield nurse_request

            blood_test_time = np.random.randint(0, 10)
            yield self.env.timeout(blood_test_time)

            self.nurse.release(nurse_request)

    def get_ecg_test(self, patient):
        print(f"Patient{patient.id} arrives for ECG test")
        with self.admin_staff.request() as admin_staff_request:
            yield admin_staff_request

            # ecg_time = np.random.randint(10)
            yield self.env.timeout(5)

            with self.doctor.request() as doctor_request:
                yield doctor_request

                # Doctor signs the ECG report
                # Send patient to ED
                yield self.env.timeout(1)

                self.doctor.release(doctor_request)
                self.admin_staff.release(admin_staff_request)

        # with self.nurse.request() as nurse_request:
        #     yield nurse_request
        #
        #
        #     self.nurse.release(nurse_request)

    def get_diagnostic_tests(self, patient):
        diag_tests = np.random.randint(0, 7)
        diag_tests = f"{diag_tests:2b}"
        print(diag_tests)
        for index, val in enumerate(diag_tests):
            if val == "1":
                if index == 0:
                    print(f"Send patient{patient.id} for ECG test")
                    yield self.env.process(self.get_ecg_test(patient))
                    print("ECG complete. Send back to get CTAS results")
                elif index == 1:
                    print(f"Send patient{patient.id} for urine test")
                    yield self.env.process(self.get_urine_test(patient))
                # elif index == 2:
                #     print(f"Send patient{patient.id} for XRay test")
                #     yield self.env.process(self.get_x_ray(patient))

    def get_arrival_ctas(self, patient):
        patient.ctas_level = random.choices([1, 2, 3, 4, 5], weights=[1, 1, 2, 3, 3])
        yield self.env.timeout(3)

    def triage_process(self, patient):
        print(f"Patient{patient.id} sent to triage waiting room")
        yield self.env.process(self.enter_triage_waiting_room(patient))

        with self.nurse.request() as nurse_request:
            yield nurse_request

            # Pop patient out from triage waiting room
            print(f"Removing patient {patient.id} from triage waiting room")
            self.triage_waiting_room.remove(patient.id)

            # Wait for triage service time
            yield self.env.process(self.get_triage_time("Screening"))
            print(f"Patient{patient.id} triage screening complete")

            # Requirement to be in ED or not
            ed_requirement = self.get_screening_results()

            self.nurse.release(nurse_request)

            if ed_requirement:
                print(f"Patient{patient.id} sent to registration counter")
                # send to registration desk
                yield self.env.process(self.enter_registration_counter())

                # Re-enters the triage process
                print(f"Patient{patient.id} in triage waiting room")
                yield self.env.process(self.enter_triage_waiting_room(patient))

                # Re-assign nurse
                with self.nurse.request() as nurse_request:
                    yield nurse_request

                    # Pop patient out from triage waiting room
                    print(f"Removing patient {patient.id} from triage waiting room")
                    self.triage_waiting_room.remove(patient.id)
                    print(f"Triage waiting room: {self.triage_waiting_room}")

                    yield self.env.process(self.get_triage_time("Diagnostic"))

                    # Process 1: get diagnostic tests done
                    # Subprocess 1
                    print("Enter subprocess 1: Get diagnostic results", self.env.now)
                    yield self.env.process(self.get_diagnostic_tests(patient))
                    print(f"Patient{patient.id} back from diagnostics.", self.env.now)

                    # Process 2: get CTAS level
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
                patient.ctas_level = 6

                patient.leave_time = self.env.now
                self.patients_processed += 1

    def triage_treatment(self, patient):
        with self.doctor.request() as doctor_request:
            yield doctor_request

            print(f"Doctor assigned to Patient{patient.id} in triage treatment")

            assessment_time = np.random.exponential(1)
            yield self.env.timeout(assessment_time)

            # Not implementing the review stage for now.
            # review = patient.get_triage_treatment_review()
            # if review:
            #     print("Re-triage to higher category")
            #     patient.ctas_level = random.randint(2, 4)
            # else:

            # Treatment complete; release doctor
            self.doctor.release(doctor_request)

            patient.leave_time = self.env.now
            self.patients_processed += 1

    def enter_medication_waiting_room(self, patient):
        print(f"Patient{patient.id} enters medication waiting room")
        self.medication_waiting_room.append(patient.id)
        print(f"Medication waiting room: {self.medication_waiting_room}")

        medication_waiting_time = 3
        patient.waiting_time += medication_waiting_time

        return medication_waiting_time

    def give_medication(self, patient):
        print("Looking for medication")
        if self.medication.level < 1:
            print(f"Medication not available")
            medication_waiting_time = self.enter_medication_waiting_room(patient)
            yield self.env.timeout(medication_waiting_time)

            print(f"Medication now available")
            self.medication.put(1)

            # Pop patient from ED waiting room list
            self.medication_waiting_room.remove(patient.id)
            print(f"Medication waiting room: {self.medication_waiting_room}")

            yield self.medication.get(1)
        else:
            print(f"Medication available")
            yield self.medication.get(1)

        medication_time = 3
        yield self.env.timeout(medication_time)

    def enter_ed_waiting_room(self, patient):
        print(f"Patient{patient.id} enters ED waiting room")
        self.ed_waiting_room.append(patient.id)
        print(f"ED waiting room: {self.ed_waiting_room}")

        ed_waiting_time = np.random.exponential(5)
        # ed_waiting_time = 0.1

        patient.waiting_time += ed_waiting_time

        # Yield triage waiting time.
        yield self.env.timeout(ed_waiting_time)

    def ed_process(self, patient):
        print(f"Patient{patient.id} arrives in ED")
        yield self.env.process(self.enter_ed_waiting_room(patient))

        with self.doctor.request() as doctor_request:
            yield doctor_request

            # Pop patient from ED waiting room list
            self.ed_waiting_room.remove(patient.id)
            print(f"ED waiting room: {self.ed_waiting_room}")

            print(f"Doctor assigned to Patient{patient.id} in ED treament")
            print(f"Performing assessment on patient{patient.id} in ED")
            assessment_time = np.random.exponential(1)
            yield self.env.timeout(assessment_time)

            # Check diagnostics required (At this time subprocess not created)
            # if diagnostic_required == "Yes":
            #     pass

            # else perform procedure on patient and give medication
            procedure_time = np.random.exponential(1)
            yield self.env.timeout(procedure_time)

            # give medication
            if self.nurse.count == 0:
                print(f"Nurse count = {self.nurse.count}")
                print(f"No nurse available to give medication")

                # Doctor gives the medication
                print("Doctor gives medication")
                yield self.env.process(self.give_medication(patient))

            else:
                print("Calling available nurse")
                # Call nurse to give medication
                with self.nurse.request() as nurse_request:
                    yield nurse_request

                    yield self.env.process(self.give_medication(patient))
                    self.nurse.release(nurse_request)

            # Refer patient to ED
            refer_immediately = np.random.randint(0, 1)

            if refer_immediately:
                print(f"Patient{patient.id} referred to inpatient treatment"
                      f"immediately.")
                self.doctor.release(doctor_request)

                # Start inpatient process/treatment
                self.env.process(self.inpatient_process(patient))
            else:
                # Wait for diagnostic results/investigation
                # IDK but the diagnosis wasn't required in earlier steps.
                # maybe re-request diagnostics here.
                print("Wait for results")
                # exit()

    def enter_inpatient_waiting_room(self, patient):
        print(f"Patient{patient.id} enters inpatient waiting room")
        self.inpatient_waiting_room.append(patient.id)
        print(f"Inpatient waiting room: {self.inpatient_waiting_room}")

        inpatient_waiting_time = np.random.exponential(1)

        patient.waiting_time += inpatient_waiting_time

        # Yield triage waiting time.
        yield self.env.timeout(inpatient_waiting_time)

    def inpatient_process(self, patient):
        yield self.env.process(self.enter_inpatient_waiting_room(patient))

        with self.doctor.request() as doctor_request:
            yield doctor_request

            self.inpatient_waiting_room.remove(patient.id)

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
                yield self.env.process(self.enter_ed_waiting_room())
                self.ed_waiting_room.remove(patient.id)

                with self.doctor.request() as doctor_request:
                    yield doctor_request

                review_time = np.random.exponential(1)
                yield self.env.timeout(review_time)

                # Treatment complete; release doctor
                self.doctor.release(doctor_request)

                patient.leave_time = self.env.now
                self.patients_processed += 1

    def transfer_to_ward(self, patient):
        # Subprocess 3
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
                    yield self.env.timeout(ed_depart_time)

                    self.nurse.release(nurse_request)

                    patient.leave_time = self.env.now
                    self.patients_processed += 1

                    # release bed after the patient is treated
                    # then what does transfer from ED mean?
                    # aren't the beds in ED?
                    self.env.process(self.release_beds(patient))

    def release_beds(self, patient):
        yield self.env.timeout(np.random.exponential(1))

    def patient_flow(self, patient):
        print(f"Patient{patient.id} enters the hospital")
        with self.doctor.request() as doctor_request:
            yield doctor_request

            with self.nurse.request() as nurse_request:
                yield nurse_request

                # Yield nurse for first (arrival) triage determination
                yield self.env.process(self.get_arrival_ctas())

                if patient.ctas_level == 1 or patient.ctas_level == 2:
                    # CTAS 1 - Send patient the other way
                    print(f"Patient{patient.id} CTAS I")

                    if patient.ctas_level == 1:
                        # Send to resuscitation room
                        pass

                    # Attend tot he patient
                    yield self.env.timeout(3)

                    # Send for diagnostic tests
                    yield self.env.process(self.get_diagnostic_tests(patient))

                    # Review diagnostic results
                    yield self.env.timeout(6)

                    further_tests = np.random.randint(0, 1)

                    if further_tests == 1:
                        yield self.env.process(self.get_diagnostic_tests(patient))

                    # If external consultation needed
                    # Do not include for now
                    # Else send to inpatient process

                    # release docs and nurses and send for
                    self.nurse.release(nurse_request)
                    self.doctor.release(doctor_request)

                    self.env.process(self.inpatient_process(patient))

                else:
                    # Release nurse, doctor and start triage process
                    self.nurse.release(nurse_request)
                    self.doctor.release(doctor_request)

                    print(f"Patient{patient.id} not in CTAS I")
                    print("Entering triage process")
                    yield self.env.process(self.triage_process(patient))


def file_output(patient):
    f = open("simulation_results.csv", "a")
    f.write(f"{patient.id},{patient.ctas_level},{patient.tests},"
            f"{patient.arrival_time},{patient.leave_time},"
            f"{patient.waiting_time}\n")
    f.close()


if __name__ == "__main__":
    sim = ERSim(20, 30, 10, 10, 100)
    sim.run_simulation()

    for patient in sim.patients:
        file_output(patient)

    # for patient in sim.patients:
    #     # print(f"Patient {patient.id} waiting time = {patient.waiting_time}")
    #     print(f"Patient {patient.id} leaves the system at time = {patient.leave_time}")
    #
    # Print the results
    print(f"Patients processed: {sim.patients_processed}")
    print(sim.patients_processed, sim.sim_time)
    # if sim.patients_processed == None:
    #     print(f"No info about num patients processed received")
    #
    # Total patients produced
    print(f"Total patients generated: {sim.patient_count}")
