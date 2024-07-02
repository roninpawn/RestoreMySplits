from xml.dom.minidom import parse
import xml.dom.minidom
import os.path
from warnings import warn


def secs_from_string(string):
    if type(string) is float or type(string) is int: return string
    if string == "None": return 0

    def str_to_int(multiplier, str_find):
        nonlocal secs, start, end
        secs += int(string[start:end]) * multiplier
        start = end + 1
        end = string.find(str_find, start)

    secs, start = 0, 0
    if string.count(".") > 1:
        end = string.strip().find(".")
        str_to_int(86400, ":")
    else: end = string.strip().find(":")

    if end > -1:
        str_to_int(3600, ":")
        if end > -1:
            str_to_int(60, ".")

            # There are circumstances in which Livesplit records GameTime as H:M:S, no ms??? I guess I'll allow it?
            if end > -1:
                secs += int(string[start:end])
                secs += float(string[end:])
            else:
                warn("secs_from_string() parsed a timecode in H:M:S format. Expected H:M:S.ms.", RuntimeWarning)
            return secs
    warn(f"secs_from_string() parsed invalid string: '{string}'. 0s returned.", RuntimeWarning)
    return 0


def time_from_secs(seconds):
    if seconds == 0: return "None"
    d = seconds // 86400
    seconds -= d * 86400
    h = seconds // 3600
    seconds -= h * 3600
    m = seconds // 60
    seconds -= m * 60
    s = seconds // 1
    seconds -= s
    ms = "{0:.7f}".format(seconds).lstrip('0')
    days = f"{int(d)}." if d else ""
    return f"{days}{int(h):02d}:{int(m):02d}:{int(s):02d}{ms}".strip()


def data_by_tag(root, tag):
    elem = root.getElementsByTagName(tag)
    if len(elem):
        return elem[0].firstChild.nodeValue
    return "None"


def list_from_array(headers, arr_1d, count_text="found.", columns="{:<17} {:<17} {:<17}"):
    out_str = columns.format(*headers)
    for entry in arr_1d:
        out_str += f"\r\n{str(entry)}"
    out_str += f"\r\n{len(arr_1d)} {count_text}"
    return out_str


def to_base(path): return os.path.basename(path)


# Data container storing an ID, along with RTA and IGT times. Instantiate with 1x DOM Element or 3x int/float/str.
class IDTime:
    def __init__(self, *args):
        if len(args) == 1:
            self.id = args[0].getAttribute("id")
            self.rta = data_by_tag(args[0], "RealTime")
            self.igt = data_by_tag(args[0], "GameTime")
        elif len(args) == 3:
            self.id, self.rta, self.igt = args[0], args[1], args[2]
        else:
            warn(f'IDTime() instantiated with {len(args)} arguments. Takes 1 DOM Element or 3 values. Stored "None"')
            self.id, self.rta, self.igt = "None", "None", "None"

    def __str__(self): return "{:<17} {:<17} {:<17}".format(self.id, self.rta, self.igt)

    def rta_secs(self): return secs_from_string(self.rta)

    def igt_secs(self): return secs_from_string(self.igt)

    def is_valid(self): return self.rta_secs() + self.igt_secs() != 0


class LSSFile:
    def __init__(self, path):
        self._xml_open = False

        if self._open(path):
            self._root = self._dom.documentElement
            self.version = self._root.getAttribute("version")
            self._attempts = []             # Array of IDTimes() which contain (id, RealTime, GameTime)
            self._segments = []             # A 2d array storing [Segment name, <SplitTime> element reference]
            self._times = []                # A 2d array containing [Segment [IDTimes (id, RealTime, GameTime)]]
            self._writeQueue = []           # Array of IDTimes() indicating the proposed writes back to the file.

            print(f"\r\nAnalyzing '{self._filename}' file for compatibility...")
            self._compatible = self._validate_and_populate()

            if self._compatible < 1:
                self.close()
                if self._compatible == 0:
                    print(f"There are no restorable runs in '{self._filename}' [Code {-self._compatible}]")
                else:
                    print(f"ERROR: '{self._filename}' is not compatible with this script. [Code {-self._compatible}]")
            else:
                print(f"\r\nOpened '{self._filename}' successfully. Version {self.version} LSS file, ready.")

    # PUBLIC FUNCTIONS
    def close(self, loud=True):
        if self._xml_open:
            self._dom.unlink()
            self._xml_open = False
            if loud: print(f"Closed file '{self._filename}'.")

    def path(self): return self._file_path

    def is_loaded(self): return self._xml_open

    def show_attempts(self): return list_from_array(["ID", "RTA", "IGT"], self._attempts, "restorable runs found.")

    def is_restorable(self, attempt_id):
        if attempt_id != "None" and self._find_attempt(attempt_id) is not None: return True
        return False

    def make_plan(self, attempt_id):
        # Error Code 1: Attempt id invalid / not found.
        if attempt_id == "None": return -1

        # If attempt is valid, populate final times from <Attempt> data
        attempt_index = self._find_attempt(attempt_id)
        if attempt_id is not None:
            final_rta = self._attempts[attempt_index].rta_secs()
            final_igt = self._attempts[attempt_index].igt_secs()
        else:
            return -1

        code = 1    # Success/Warning return code
        sum_rta, sum_igt, invalid_count = 0, 0, 0
        il_stack = []

        # Pre-calculate as IL times. [index, rta_secs, igt_secs] (allows simple correction)
        for i in range(len(self._times)):
            for time in self._times[i]:
                if time.id == attempt_id:
                    if time.is_valid():
                        sum_rta += time.rta_secs()
                        sum_igt += time.igt_secs()
                    else:
                        invalid_count += 1

                    il_stack.append(IDTime(i, time.rta_secs(), time.igt_secs()))
                    break
            else:
                # If last split is missing, populate it using difference of sum and final times.
                if i == len(self._times) - 1:
                    il_stack.append(IDTime(i, round(final_rta - sum_rta, 7), round(final_igt - sum_igt, 7)))
                    sum_rta, sum_igt = final_rta, final_igt

                    # Warning Code 0: Run missing 2 or more times. Accurate restoration is not guaranteed.
                    if invalid_count > 0: code = 0
                else:
                    invalid_count += 1
                    il_stack.append(IDTime(i, 0, 0))

        sum_rta = round(sum_rta, 7)
        sum_igt = round(sum_igt, 7)
        if sum_rta != final_rta or sum_igt != final_igt:

            # Error Code 2: Sum of times doesn't match expected final. Too many missing splits. Run corrupt.
            if invalid_count != 1: return -2

            # If just one split missing, populate it using difference of sum and final times.
            else:
                for i in range(len(il_stack)):
                    if not il_stack[i].is_valid():
                        il_stack[i] = IDTime(i, final_rta - sum_rta, final_igt - sum_igt)
                        break

        # Finally, populate self._writeQueue with segment names and summed times in H:M:S.ms format.
        sum_rta, sum_igt = 0, 0
        self._writeQueue = []

        for il in il_stack:
            il_rta = il.rta_secs()
            il_igt = il.igt_secs()
            sum_rta += il_rta
            sum_igt += il_igt
            self._writeQueue.append(IDTime(self._segments[int(il.id)][0],
                                           time_from_secs(sum_rta) if il_rta else "None",
                                           time_from_secs(sum_igt) if il_igt else "None"))
        # Success Code
        return code

    def show_plan(self): return list_from_array(["Segment", "RTA", "IGT"], self._writeQueue, "changes proposed.")

    def save_plan(self, output_file):
        # Error Code 1: Invalid or inaccessible path/filename provided.
        if not os.path.exists(output_file) and not os.access(os.path.dirname(output_file), os.W_OK):
            return -1
        else:
            # Error Code 2: Failed to update values in memory.
            if not self._write_to_xml():
                return -2
            else:
                try:
                    self._dom.writexml(open(output_file, 'w'))
                except:
                    # Error Code 3: DOM failed to save to the output file.
                    return -3
                else:
                    # Success Code
                    return 1

    # PRIVATE FUNCTIONS
    def _open(self, file_path):
        self._file_path = file_path
        self._filename = to_base(file_path)

        if self._xml_open: self.close()
        if not os.path.isfile(file_path): print(f"ERROR: Splits file '{self._filename}' not found.")
        else:
            try:    self._dom = xml.dom.minidom.parse(file_path)
            except: print(f"ERROR: Could not open '{self._filename}' as an XML document.")
            else:
                self._xml_open = True
                return True
        return False

    def _find_attempt(self, attempt_id):
        for i in range(len(self._attempts)):
            if self._attempts[i].id == attempt_id: return i
        return None

    def _validate_and_populate(self):
        nav_elem = self._root.getElementsByTagName("AttemptHistory")

        # Error Code 1: No, or multiple, <AttemptHistory> element(s) found
        if len(nav_elem) != 1: return -1
        else:
            nav_elem = nav_elem[0].getElementsByTagName("Attempt")

            # Only store <Attempt>'s that finished.
            for attempt in nav_elem:
                if attempt.hasChildNodes():
                    idt = IDTime(attempt)
                    if idt.is_valid(): self._attempts.append(idt)

            # Error Code 0: No completed runs found in <AttemptHistory>
            if not len(self._attempts): return 0
            else:

                # Segment nodes, their names, their <SplitTime> nodes, and the <Time>'s they contain are stored.
                nav_elem = self._root.getElementsByTagName("Segments")

                # ERROR Code 2: No <Segments> element found
                if not len(nav_elem): return -2
                else:
                    segments = nav_elem[0].getElementsByTagName("Segment")

                    # ERROR Code 3: No <Segment> elements found
                    if not len(segments): return -3
                    else:
                        for i in range(len(segments)):
                            split_times_ref = segments[i].getElementsByTagName("SplitTimes")

                            # ERROR Code 4: No, or multiple, <SplitTimes> element(s) found
                            if len(split_times_ref) != 1: return -4
                            else:
                                self._segments.append([data_by_tag(segments[i], "Name"), split_times_ref[0]])
                                times = segments[i].getElementsByTagName("Time")

                                # Only store <Time>'s that belong to valid <Attempt>'s
                                id_times = []
                                for time in times:
                                    time_id = time.getAttribute("id")
                                    if time_id != "":
                                        for attempt in self._attempts:
                                            if time_id == attempt.id:
                                                id_times.append(IDTime(time))
                                                break
                                self._times.append(id_times)

        # Success Code
        return 1

    def _write_to_xml(self):
        if not self._xml_open or not len(self._writeQueue): return False

        # Pre-made nodes to clone.
        new_pb = self._dom.createElement("SplitTime").setAttribute("name", "Personal Best")
        new_rta = self._dom.createElement("RealTime")
        new_igt = self._dom.createElement("GameTime")

        # Conform segment <SplitTimes> to contain one <SplitTime name="Personal Best"> with no children.
        for i in range(len(self._writeQueue)):
            split_times = self._segments[i][1].getElementsByTagName("SplitTime")
            if not len(split_times):
                # Add a <SplitTime name="Personal Best"> node if missing.
                write_node = self._segments[i][1].appendChild(new_pb.cloneNode(True))
            else:
                for j in range(len(split_times)):
                    if split_times[j].getAttribute("name").strip() == "Personal Best":
                        write_node = split_times[j]
                        # Delete any existing <RealTime> and or <GameTime> entries.
                        while split_times[j].hasChildNodes():
                            split_times[j].removeChild(split_times[j].firstChild)
                        break
                else:
                    # Add a <SplitTime name="Personal Best"> node if missing.
                    write_node = self._segments[i][1].appendChild(new_pb.cloneNode(True))

            # Insert new values.
            if self._writeQueue[i].rta_secs() > 0:
                write_node.appendChild(new_rta.cloneNode(1)).appendChild(self._dom.createTextNode(self._writeQueue[i].rta))
            if self._writeQueue[i].igt_secs() > 0:
                write_node.appendChild(new_igt.cloneNode(1)).appendChild(self._dom.createTextNode(self._writeQueue[i].igt))
        return True
