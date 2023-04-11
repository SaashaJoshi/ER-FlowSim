import random
import numpy as np
import simpy
from patients import Patient


class ERSim:
    """
    ERSim: Emergency Room Simulation class creates objects to simulate
    an emergency room scenario
    """

    patient_count = 0

    def __init__(self, num_doctors, num_nurses, num_beds, num_admin_staff, num_consultants, sim_time, seed=100):

        random.seed(seed)
        self.env = simpy.Environment()
        self.num_doctors = num_doctors
        self.num_nurses = num_nurses
        self.num_beds = num_beds
        self.sim_time = sim_time

        self.patients = []
        self.doctor = simpy.Resource(self.env, capacity=num_doctors)
        self.nurse = simpy.Resource(self.env, capacity=num_nurses)
        self.admin_staff = simpy.Resource(self.env, capacity=num_admin_staff)
        self.consultant = simpy.Resource(self.env, capacity=num_consultants)

        self.bed = simpy.Resource(self.env, capacity=num_beds)
        self.ecg_machine = simpy.Resource(self.env, capacity=5)
        self.ct_machine = simpy.Resource(self.env, capacity=5)
        self.x_ray_machine = simpy.Resource(self.env, capacity=5)

        self.inter_arrival_time = 0
        self.triage_waiting_room = []
        self.ed_waiting_room = []
        self.medication_waiting_room = []
        self.inpatient_waiting_room = []
        self.triage_waiting_room_len = 0
        self.ed_waiting_room_len = 0
        self.medication_waiting_room_len = 0
        self.inpatient_waiting_room_len = 0

        self.medication = simpy.Container(self.env, init=0)
        self.blood_tubes = simpy.Container(self.env, capacity=30)
        # self.stationary = simpy.Container(self.env, capacity=30)
        self.patients_processed = 0

    def run_simulation(self):
        self.env.process(self.generate_patients())
        self.env.run(until=self.sim_time)
        print("Resource count: ", self.doctor.count, self.nurse.count,
              self.admin_staff.count, self.consultant.count)

    def generate_patients(self):
        while True:
            print("Patient produced")

            # Check probability of CTAS I-III or IV-V
            weights = [0.6186, 0.3814]
            ctas_level = random.choices([1, 2], weights=weights)[0]
            # self.inter_arrival_time = random.expovariate(1.66)
            if ctas_level == 1:
                self.inter_arrival_time = random.expovariate(1.66)
                # self.inter_arrival_time = random.expovariate(6.6)
                # self.inter_arrival_time = random.expovariate(4)
                # self.inter_arrival_time = random.expovariate(0.67)
            elif ctas_level == 2:
                # self.inter_arrival_time = random.expovariate(6.6)
                self.inter_arrival_time = random.expovariate(1.2)
                # self.inter_arrival_time = random.expovariate(2)
                # self.inter_arrival_time = random.expovariate(0.046)

            ERSim.patient_count += 1
            patient = Patient(self.env.now)
            self.patients.append(patient)
            self.env.process(self.patient_flow(patient))
            yield self.env.timeout(self.inter_arrival_time)

    def get_screening_results(self):
        return random.choices([0, 1], weights=[9, 1])

    def enter_registration_counter(self):
        with self.admin_staff.request() as admin_staff_request:
            yield admin_staff_request

            registration_time = np.random.triangular(3, 4, 8)
            yield self.env.timeout(registration_time)

            self.admin_staff.release(admin_staff_request)

    def enter_triage_waiting_room(self, patient):
        print(f"Patient {patient.id} enters triage waiting room")
        self.triage_waiting_room.append(patient.id)
        print(f"Triage waiting room: {self.triage_waiting_room}")

        # Max waiting room len
        self.triage_waiting_room_len = max(self.triage_waiting_room_len, len(self.triage_waiting_room))
        yield self.env.timeout(0)

    def get_triage_time(self, scale):
        if scale == "Screening":
            time = np.random.triangular(4, 6, 8)
            yield self.env.timeout(time)
        elif scale == "Diagnostic":
            time = np.random.triangular(4, 6, 8)
            yield self.env.timeout(time)

    def get_x_ray(self, patient, staff_request=1):
        if staff_request == 1:
            with self.doctor.request() as doctor_request:
                yield doctor_request

                # Doctor approves need for an X-ray
                # yield self.env.timeout(3)

                # Should I call a nurse here or admin staff?
                with self.nurse.request() as nurse_request:
                    yield nurse_request

                    with self.x_ray_machine.request() as x_ray_machine:
                        yield x_ray_machine

                        # Time for x_ray to complete
                        x_ray_time = np.random.triangular(10, 18, 30)
                        yield self.env.timeout(x_ray_time)

                        self.x_ray_machine.release(x_ray_machine)

                        # Assign CTAS level
                        patient.ctas_level = patient.get_ctas_level()

                        self.x_ray_machine.release(x_ray_machine)
                        # Release nurse and send to triage doc
                        self.nurse.release(nurse_request)
                        self.doctor.release(doctor_request)
        else:
            with self.x_ray_machine.request() as x_ray_machine:
                yield x_ray_machine

                # Time for x_ray to complete
                x_ray_time = np.random.triangular(10, 18, 30)
                yield self.env.timeout(x_ray_time)

                self.x_ray_machine.release(x_ray_machine)

                # Assign CTAS level
                patient.ctas_level = patient.get_ctas_level()

                self.x_ray_machine.release(x_ray_machine)

    def get_urine_test(self, patient):
        print(f"Patient{patient.id} arrives for urine test")
        with self.nurse.request() as nurse_request:
            yield nurse_request

            urine_test_time = np.random.triangular(5, 7, 12)
            yield self.env.timeout(urine_test_time)

            # Assign CTAS level
            patient.ctas_level = patient.get_ctas_level()

            self.nurse.release(nurse_request)

    def get_ecg_test(self, patient):
        print(f"Patient{patient.id} arrives for ECG test")
        with self.admin_staff.request() as admin_staff_request:
            yield admin_staff_request

            # ecg_time = np.random.randint(10)
            ecg_time = np.random.triangular(45, 55, 60)
            yield self.env.timeout(ecg_time)

            with self.doctor.request() as doctor_request:
                yield doctor_request

                # Doctor signs the ECG report
                # Send patient to ED
                # yield self.env.timeout(1)

                # Assign CTAS level
                patient.ctas_level = patient.get_ctas_level()

                self.doctor.release(doctor_request)
                self.admin_staff.release(admin_staff_request)

    def get_blood_test(self, patient):
        with self.nurse.request() as nurse_request:
            yield nurse_request

            print(f"Patient{patient.id} arrives for blood test")
            print("Looking for blood tubes")
            if self.blood_tubes.level < 1:
                print(f"Blood tubes not available not available")

                # Time to get the blood tubes
                time = np.random.triangular(1, 2, 3)
                yield self.env.timeout(time)
                self.medication.put(1)
                print(f"Blood tubes now available")

                # Take blood sample
                yield self.medication.get(1)
            else:
                print(f"Medication available")
                yield self.medication.get(1)

            # Blood sample taken.
            # Get stationary - skip this useless part.
            blood_test_time = np.random.triangular(5, 7, 12)
            yield self.env.timeout(blood_test_time)

            self.nurse.release(nurse_request)

    def get_ct_scan(self):
        with self.doctor.request() as doctor_request:
            yield doctor_request

            ct_scan_time = np.random.triangular(45, 55, 60)
            yield self.env.timeout(ct_scan_time)

            self.doctor.release(doctor_request)

    def get_radiological_test(self, patient):
        # Doctor fills request form
        # Check if CT or X-Ray required.
        choice = np.random.randint(0, 1)

        if choice == 1:
            patient.tests.append("ED X-Ray")
            # Send for X-Ray
            yield self.env.process(self.get_x_ray(patient, staff_request=1))
        elif choice == 0:
            patient.tests.append("ED CT")
            with self.admin_staff.request() as admin_staff_request:
                yield admin_staff_request

                # Admin/Radiologist approves scan request
                time = np.random.triangular(1, 2, 3)
                yield self.env.timeout(time)

                # Get CT
                yield self.env.process(self.get_ct_scan())

                self.admin_staff.release(admin_staff_request)

    def get_diagnostic_tests(self, patient, department):
        if department == "Triage":
            print(f"Patient{patient.id} getting Triage tests")
            triage_diag_tests = random.choice([0, 1, 2, 3, 4, 5, 6, 7])
            # triage_diag_tests = random.choice([1, 2, 3])
            triage_diag_tests = f"{triage_diag_tests:2b}"
            print(triage_diag_tests)

            for index, val in enumerate(triage_diag_tests):
                if val == "1":
                    # if triage_diag_tests == 1:
                    if index == 0:
                        patient.tests.append("Triage ECG")
                        print(f"Send patient{patient.id} for ECG test")
                        yield self.env.process(self.get_ecg_test(patient))
                        print("ECG complete. Send back to get CTAS results")
                    # elif triage_diag_tests == 2:
                    elif index == 1:
                        patient.tests.append("Triage Urine")
                        print(f"Send patient{patient.id} for urine test")
                        yield self.env.process(self.get_urine_test(patient))
                    elif index == 2:
                        # elif triage_diag_tests == 3:
                        patient.tests.append("Triage X-Ray")
                        print(f"Send patient{patient.id} for XRay test")
                        yield self.env.process(self.get_x_ray(patient, staff_request=1))

        elif department == "ED":
            print(f"Patient{patient.id} getting ED tests")
            # Doctor always needed for ED diagnostic tests!
            ed_diag_tests = random.choice([0, 1, 2, 3])
            ed_diag_tests = f"{ed_diag_tests:2b}"
            print(ed_diag_tests)

            for index, val in enumerate(ed_diag_tests):
                if val == "1":
                    if index == 0:
                        # if ed_diag_tests == 0:
                        patient.tests.append("ED Blood Test")
                        print(f"Send patient{patient.id} for blood test")
                        yield self.env.process(self.get_blood_test(patient))
                    elif index == 1:
                        # elif ed_diag_tests == 1:
                        print(f"Send patient{patient.id} for radiological test")
                        yield self.env.process(self.get_radiological_test(patient))

    def get_arrival_ctas(self, patient):
        # patient.ctas_level = random.choices([1, 2, 3, 4, 5], weights=[1, 1, 2, 3, 3])
        patient.ctas_level = random.choice([0, 1, 2, 3, 4, 5])
        time = np.random.triangular(1, 2, 3)
        yield self.env.timeout(time)

    def get_consultation(self, patient):
        with self.consultant.request() as consultant_request:
            yield consultant_request

            if patient.ctas_level == 1 or patient.ctas_level == 2:
                # should be efficient with less/more time/more skill
                # Consultation for CTAS I-II patients

                # Time for consultation
                time = np.random.triangular(10, 15, 30)
                yield self.env.timeout(time)
            else:
                # Time for consultation
                time = np.random.triangular(5, 10, 30)
                yield self.env.timeout(time)

                # Re-triage to higher CTAS
                # patient.ctas_level = random.choices([3, 4, 5], weights=[3, 3, 4])

            self.consultant.release(consultant_request)

    def triage_process(self, patient):
        print(f"Patient{patient.id} sent to triage waiting room")
        time_enter_waiting_room = self.env.now
        yield self.env.process(self.enter_triage_waiting_room(patient))

        with self.nurse.request() as nurse_request:
            yield nurse_request

            # Pop patient out from triage waiting room
            print(f"Removing patient {patient.id} from triage waiting room")
            self.triage_waiting_room.remove(patient.id)

            time_exit_waiting_room = self.env.now
            time = time_exit_waiting_room - time_enter_waiting_room
            patient.triage_waiting_time += time

            # Wait for triage service time
            yield self.env.process(self.get_triage_time("Screening"))
            print(f"Patient{patient.id} triage screening complete")

            self.nurse.release(nurse_request)

        # Requirement to be in ED or not
        ed_requirement = self.get_screening_results()

        if ed_requirement:
            print(f"Patient{patient.id} sent to registration counter")
            # send to registration desk
            yield self.env.process(self.enter_registration_counter())

            # Re-enters the triage process - Diagnostic tests
            print(f"Patient{patient.id} in triage waiting room")
            yield self.env.process(self.enter_triage_waiting_room(patient))
            time_enter_waiting_room = self.env.now

            # Re-assign nurse
            with self.nurse.request() as nurse_request_2:
                yield nurse_request_2

                # Pop patient out from triage waiting room
                print(f"Removing patient {patient.id} from triage waiting room")
                self.triage_waiting_room.remove(patient.id)
                print(f"Triage waiting room: {self.triage_waiting_room}")

                time_exit_waiting_room = self.env.now
                time = time_exit_waiting_room - time_enter_waiting_room
                patient.triage_waiting_time += time

                # Nurse assesses the patient and sends to diagnostics
                # yield self.env.timeout(5)

                # release nurse and send to triage treatment or ed
                self.nurse.release(nurse_request_2)

            # Process 1: get diagnostic tests done
            # Subprocess 1
            print("Enter subprocess 1: Get diagnostic results", self.env.now)
            yield self.env.process(self.get_diagnostic_tests(patient, "Triage"))
            print(f"Patient{patient.id} back from diagnostics.", self.env.now)

            # Process 2: get CTAS level.
            # CTAS level can also be given while diagnostics are getting done
            if patient.ctas_level is None:
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
            patient.ctas_level = 6

            patient.leave_time = self.env.now
            self.patients_processed += 1

    def triage_treatment(self, patient):
        with self.doctor.request() as doctor_request:
            yield doctor_request

            print(f"Doctor assigned to Patient{patient.id} in triage treatment")

            assessment_time = np.random.triangular(4, 6, 8)
            yield self.env.timeout(assessment_time)

            # Medication time
            # Wait for nurse
            with self.nurse.request() as nurse_request:
                yield nurse_request

                yield self.env.process(self.give_medication(patient))

                self.nurse.release(nurse_request)

            # Review/Consultation step
            # Patient can be re-triaged to higher CTAS level
            consultation = np.random.randint(0, 1)

            if consultation == 1:
                yield self.env.process(self.get_consultation(patient))

                # If re-triaged send to ED
                if patient.ctas_level < 5:
                    # Release triage doctor
                    self.doctor.release(doctor_request)
                    self.env.process(self.ed_process(patient))

            # Discharge patient
            patient.leave_time = self.env.now
            self.patients_processed += 1

            # Treatment complete; release doctor
            self.doctor.release(doctor_request)

    def enter_medication_waiting_room(self, patient):
        print(f"Patient{patient.id} enters medication waiting room")
        self.medication_waiting_room.append(patient.id)
        print(f"Medication waiting room: {self.medication_waiting_room}")

        # Max waiting room len
        self.medication_waiting_room_len = max(self.medication_waiting_room_len, len(self.medication_waiting_room))

        medication_waiting_time = np.random.triangular(1, 2, 3)
        patient.medication_waiting_time += medication_waiting_time

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

        medication_time = np.random.triangular(1, 2, 3)
        yield self.env.timeout(medication_time)

    def enter_ed_waiting_room(self, patient):
        print(f"Patient{patient.id} enters ED waiting room")
        self.ed_waiting_room.append(patient.id)
        print(f"ED waiting room: {self.ed_waiting_room}")

        # Max waiting room len
        self.ed_waiting_room_len = max(self.ed_waiting_room_len, len(self.ed_waiting_room))
        yield self.env.timeout(0)

    def ed_process(self, patient):
        print(f"Patient{patient.id} arrives in ED")
        yield self.env.process(self.enter_ed_waiting_room(patient))
        time_enter_waiting_room = self.env.now

        with self.doctor.request() as doctor_request:
            yield doctor_request

            # Pop patient from ED waiting room list
            self.ed_waiting_room.remove(patient.id)
            print(f"ED waiting room: {self.ed_waiting_room}")

            time_exit_waiting_room = self.env.now
            time = time_exit_waiting_room - time_enter_waiting_room
            patient.ed_waiting_time += time

            print(f"Doctor assigned to Patient{patient.id} in ED treatment")
            print(f"Performing assessment on patient{patient.id} in ED")
            assessment_time = np.random.triangular(4, 6, 8)
            yield self.env.timeout(assessment_time)

            # Check diagnostics required
            # Subprocess 2
            diagnostic_required = random.randint(0, 1)
            if diagnostic_required == 1:
                self.doctor.release(doctor_request)
                yield self.env.process(self.get_diagnostic_tests(patient, "ED"))
            else:
                # else perform procedure on patient and give medication
                procedure_time = np.random.triangular(4, 6, 10)
                yield self.env.timeout(procedure_time)
                self.doctor.release(doctor_request)

        # give medication
        if self.nurse.count == 0:
            print(f"Nurse count = {self.nurse.count}")
            print(f"No nurse available to give medication")

            # Doctor gives the medication
            print("Doctor gives medication")
            with self.doctor.request() as doctor_request:
                yield doctor_request

                yield self.env.process(self.give_medication(patient))
                self.doctor.release(doctor_request)

        else:
            print("Calling available nurse")
            # Call nurse to give medication
            with self.nurse.request() as nurse_request:
                yield nurse_request

                yield self.env.process(self.give_medication(patient))
                self.nurse.release(nurse_request)

        with self.doctor.request() as doctor_request:
            yield doctor_request

            # Refer patient to ED
            refer_immediately = np.random.randint(0, 1)

            if refer_immediately:
                print(f"Patient{patient.id} referred to inpatient treatment"
                      f"immediately.")
                self.doctor.release(doctor_request)

                # Start inpatient process/treatment
                self.env.process(self.inpatient_process(patient))
            else:
                # Wait for results
                # print("Wait for results")

                # Perform further diagnosis/investigation
                # Subprocess 2, see, required again!
                # further_investigation = random.choices([0, 1], weights=[9.9, 0.1])
                # if further_investigation == 1:
                #     self.doctor.release(doctor_request)
                #     yield self.env.process(self.get_diagnostic_tests(patient, "ED"))
                # else:
                # yield self.env.process(self.get_consultation(patient))
                self.doctor.release(doctor_request)

        disposition_decision = random.randint(0, 1)
        if disposition_decision == 1:
            # Refer further to inpatient department
            self.env.process(self.inpatient_process(patient))
        else:
            patient.leave_time = self.env.now
            self.patients_processed += 1

    def enter_inpatient_waiting_room(self, patient):
        print(f"Patient{patient.id} enters inpatient waiting room")
        self.inpatient_waiting_room.append(patient.id)
        print(f"Inpatient waiting room: {self.inpatient_waiting_room}")

        # Max waiting room len
        self.inpatient_waiting_room_len = max(self.inpatient_waiting_room_len, len(self.inpatient_waiting_room))
        yield self.env.timeout(0)

    def inpatient_process(self, patient):
        yield self.env.process(self.enter_inpatient_waiting_room(patient))
        time_enter_waiting_room = self.env.now

        with self.doctor.request() as doctor_request:
            yield doctor_request

            self.inpatient_waiting_room.remove(patient.id)

            time_exit_waiting_room = self.env.now
            time = time_exit_waiting_room - time_enter_waiting_room
            patient.inpatient_waiting_time += time

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
            yield self.env.process(self.enter_ed_waiting_room(patient))
            time_enter_waiting_room = self.env.now

            with self.doctor.request() as doctor_request:
                yield doctor_request

                self.ed_waiting_room.remove(patient.id)
                time_exit_waiting_room = self.env.now
                time = time_exit_waiting_room - time_enter_waiting_room
                patient.ed_waiting_time += time

                review_time = np.random.triangular(1, 2, 3)
                yield self.env.timeout(review_time)

                patient.leave_time = self.env.now
                self.patients_processed += 1

                # Treatment complete; release doctor
                self.doctor.release(doctor_request)

    def transfer_to_ward(self, patient):
        # Subprocess 3
        # Initiates transfer process

        # Admin checks if beds available patient to bed/room
        with self.admin_staff.request() as admin_staff_request:
            yield admin_staff_request

            with self.bed.request() as bed_request:
                yield bed_request

                # Admin staff helps transfer out of ED
                ed_depart_time = np.random.triangular(4, 7, 9)
                yield self.env.timeout(ed_depart_time)

                patient.leave_time = self.env.now
                self.patients_processed += 1

                # release bed after the patient is treated
                # self.env.process(self.release_beds())

                self.bed.release(bed_request)
                self.admin_staff.release(admin_staff_request)

    def release_beds(self):
        yield self.env.timeout(np.random.triangular(30, 50, 90))

    def ctas_1_process(self, patient):
        # If CTAS-I take to resuscitation room then send for tests.
        # Else directly attend and send for tests.
        if patient.ctas_level == 1:
            # Send to resuscitation room
            transfer_time = np.random.triangular(1, 2, 4)
            yield self.env.timeout(transfer_time)

        # Attend to the patient
        time = np.random.triangular(2, 4, 9)
        yield self.env.timeout(time)

    def patient_flow(self, patient):
        print(f"Patient{patient.id} enters the hospital")
        with self.doctor.request() as doctor_request:
            yield doctor_request

            with self.nurse.request() as nurse_request:
                yield nurse_request

                # Yield nurse for first (arrival) triage determination
                yield self.env.process(self.get_arrival_ctas(patient))

                # # Release nurse, doctor and start triage process
                # self.nurse.release(nurse_request)
                # self.doctor.release(doctor_request)

                if patient.ctas_level == 1:
                    # CTAS 1 - Send patient the other way
                    print(f"Patient{patient.id} CTAS I")
                    yield self.env.process(self.ctas_1_process(patient))

                    # Send for ED diagnostic tests
                    yield self.env.process(self.get_diagnostic_tests(patient, "ED"))

                    # Review diagnostic results
                    # If further tests required send to subprocess 2
                    # Else check if consultation needed
                    # further_tests = random.choices([0, 1], weights=[9, 1])
                    #
                    # if further_tests == 1:
                    #     yield self.env.process(self.get_diagnostic_tests(patient, "ED"))
                    # else:

                    # Check if external consultation needed
                    # Else send to inpatient doctor.
                    consultation = np.random.randint(0, 1)

                    if consultation:
                        yield self.env.process(self.get_consultation(patient))

                    # Finally send to inpatient process
                    # release docs and nurses and send for inpatient process
                    self.nurse.release(nurse_request)
                    self.doctor.release(doctor_request)
                    self.env.process(self.inpatient_process(patient))

                elif patient.ctas_level > 1:
                    print(f"Patient{patient.id} not in CTAS I")
                    print("Entering triage process")
                    # Release nurse, doctor and start triage process
                    self.nurse.release(nurse_request)
                    self.doctor.release(doctor_request)
                    self.env.process(self.triage_process(patient))


def file_output(sim):
    f = open("results/simulation_results_system_1_5.csv", "a")

    f.write("Patient ID, CTAS Level, Tests, "
            "Arrival Time, Departure Time, LOS, "
            "Triage Waiting Time, ED Waiting Time, "
            "Medication Waiting Time, Inpatient Waiting Time, "
            "Triage Waiting Room Length, ED Waiting Room Length, "
            "Medication Waiting Room Length, Inpatient Waiting Room Length \n"
            )

    for patient in sim.patients:
        f.write(f"{patient.id},{patient.ctas_level}, {patient.tests}, "
                f"{patient.arrival_time},{patient.leave_time}, {patient.leave_time - patient.arrival_time},"
                f"{patient.triage_waiting_time}, {patient.ed_waiting_time},"
                f"{patient.medication_waiting_time}, {patient.inpatient_waiting_time},"
                f"{sim.triage_waiting_room_len}, {sim.ed_waiting_room_len},"
                f"{sim.medication_waiting_room_len}, {sim.inpatient_waiting_room_len}\n")

    f.close()


if __name__ == "__main__":
    # sim = ERSim(100, 100, 50, 70, 50, 43800, 100) # minutes in month NOT BAD!!!!
    # sim = ERSim(20, 30, 10, 10, 10080) # minutes in week
    # sim = ERSim(100, 100, 100, 100, 1000)
    sim = ERSim(100, 100, 50, 70, 50, 10080, 35)
    # sim = ERSim(30, 50, 1, 10, 5, 2880, 100)  # minutes in 2 days
    # sim = ERSim(50, 50, 50, 50, 20, 10080, 100)  # minutes in week PERFECT!
    sim.run_simulation()

    # sim = ERSim(50, 50, 50, 50, 20, 10080, 100)  # minutes in week PERFECT!

    file_output(sim)

    # for patient in sim.patients:
    #     # print(f"Patient {patient.id} waiting time = {patient.waiting_time}")
    #     print(f"Patient {patient.id} leaves the system at time = {patient.leave_time}")
    #
    # Print the results
    print(f"Patients processed: {sim.patients_processed}")
    print(sim.patients_processed, sim.sim_time, sim.patient_count)
    # if sim.patients_processed == None:
    #     print(f"No info about num patients processed received")
    #
    # Total patients produced
    print(f"Total patients generated: {sim.patient_count}")
