#!/usr/bin/env python3

import time
import subprocess as sp
from csv import writer
from dataclasses import dataclass, field
from typing import Optional, Any
from flask import Flask, jsonify
from stressmon import CPUInfo, CPUFreq, CPUTemp, CPUUsage, CPUWatts, SysFan, \
                      MemUsage, DriveTemp, GPUData, UpdatePool

@dataclass
class OutputData:
    """Data for output updatepool functions"""
    csv_fn: Optional[str] = field(default=None)
    summary_fn: Optional[str] = field(default=None)
    run_time: Optional[float] = field(default=None)
    iterations: Optional[int] = field(default=None)
    watts: Optional[CPUWatts] = field(default=None)
    mhz: Optional[CPUFreq] = field(default=None)
    ctemps: Optional[CPUTemp] = field(default=None)
    fans: Optional[SysFan] = field(default=None)
    gpus: Optional[GPUData] = field(default=None)
    drives: Optional[DriveTemp] = field(default=None)
    usage: Optional[CPUUsage] = field(default=None)
    mem: Optional[MemUsage] = field(default=None)
    data: Optional[list] = field(default=None)
    time: Optional[str] = field(default=None)
    model_name: Optional[str] = field(default=None)

def get_model_name() -> str:
    """
    Retrieve the model name of the system.

    This function uses the `dmidecode` command to extract the system's model name. 
    It specifically filters for the 'Version' field from the output of `dmidecode -t 1`, 
    which contains information about the system's hardware. The command is run with 
    superuser privileges using `sudo`.

    Returns:
        str: The model name of the system.

    Raises:
        subprocess.CalledProcessError: If the command execution fails.
    """
    return sp.run(["sudo dmidecode -t 1 | grep Version | awk '{print $2}'"],
                  shell=True,
                  check=True,
                  stdout=sp.PIPE).stdout.decode('utf-8').strip()

def format_line(items: list, column_widths: list, justifications: list):
    """
    Formats a single line with specified column widths and justifications.

    This function takes a list of items and formats them into a single line based on the
    provided column widths and justifications. It constructs a format string dynamically
    to align each item according to the specified justification and width.

    Args:
        items (list): A list of items to be formatted into the line.
        column_widths (list): A list of integers specifying the width of each column.
        justifications (list): A list of strings specifying the justification for each column.
                               Each string should be one of '>', '<', or '^', representing
                               right, left, or center alignment, respectively.

    Returns:
        str: A formatted string representing a single line with the specified column widths
             and justifications.

    Example:
        >>> items = ["Name", "Age", "City"]
        >>> column_widths = [10, 5, 15]
        >>> justifications = ['<', '>', '^']
        >>> format_line(items, column_widths, justifications)
        'Name       Age  City           \n'
    """
    line_format = "".join(
        ["{:" + just + str(width) + "}" for just, width in zip(justifications, column_widths)]
    ) + "\n"
    return line_format.format(*items)

def write_csv(output_data: OutputData) -> None:
    """
    Append current data to a log CSV file.

    This function opens the specified CSV file in append mode and writes the current data
    to it as a new row. The data is appended to the end of the file without modifying 
    existing content.

    Args:
        output_data (OutputData): An instance of the OutputData class containing the
                                  filename of the CSV file and the data to be written.
                                  - output_data.csv_fn (str): The filename of the CSV file.
                                  - output_data.data (list): A list of data items to be
                                                             written as a row in the CSV file.

    Returns:
        None

    Example:
        >>> class OutputData:
        >>>     def __init__(self, csv_fn, data):
        >>>         self.csv_fn = csv_fn
        >>>         self.data = data
        >>>
        >>> output_data = OutputData('log.csv', ['2024-07-30', 'example', 123])
        >>> write_csv(output_data)

    Note:
        Ensure that the `OutputData` class is defined with the appropriate attributes 
        before using this function.
    """
    with open(file=output_data.csv_fn, mode='a', encoding='utf-8') as outfile:
        csv_writer = writer(outfile)
        csv_writer.writerow(output_data.data)

def write_summary(output_data: OutputData) -> None:
    """
    Write the current state to a summary log file.

    This function generates a detailed summary of the system's current state, including
    information about the CPU, memory, temperatures, power consumption, fans, GPUs, and
    drives. The summary is formatted into a structured text and written to a specified
    summary log file.

    Args:
        output_data (OutputData): An instance of the OutputData class containing various
                        system state information and filenames for output.
                        Attributes should include:
                        - output_data.csv_fn (str): The filename of the CSV file.
                        - output_data.summary_fn (str): The filename of the summary file.
                        - output_data.time (str): The start time of the logging.
                        - output_data.run_time (str): The runtime duration.
                        - output_data.mhz (object): An object representing CPU frequencies.
                        - output_data.ctemps (object): An object representing core temperatures.
                        - output_data.watts (object): An object representing power consumption.
                        - output_data.fans (object): An object representing fan speeds.
                        - output_data.gpus (object): An object representing GPU information.
                        - output_data.drives (object): An object representing drive information.
                        - output_data.usage (object): An object representing CPU usage.
                        - output_data.mem (object): An object representing memory information.
                        - output_data.model_name (str): The model name of the system.

    Returns:
        None

    Example:
        >>> class OutputData:
        >>>     def __init__(self, csv_fn, summary_fn, time, run_time, mhz, ctemps, watts,
        >>>                  fans, gpus, drives, usage, mem, model_name):
        >>>         self.csv_fn = csv_fn
        >>>         self.summary_fn = summary_fn
        >>>         self.time = time
        >>>         self.run_time = run_time
        >>>         self.mhz = mhz
        >>>         self.ctemps = ctemps
        >>>         self.watts = watts
        >>>         self.fans = fans
        >>>         self.gpus = gpus
        >>>         self.drives = drives
        >>>         self.usage = usage
        >>>         self.mem = mem
        >>>         self.model_name = model_name
        >>>
        >>> output_data = OutputData('log.csv', 'summary.txt', '2024-07-30 12:00', '1h 30m',
        >>>                         mhz, ctemps, watts, fans, gpus, drives, usage, mem, 'Model X')
        >>> write_summary(output_data)
    """
    def append_formatted_section(title, data_rows, headers, col_widths, justifications):
        if data_rows:
            lines.append(title)
            lines.append(format_line(headers, col_widths, justifications))
            for row in data_rows:
                lines.append(format_line(row, col_widths, justifications))
            lines.append("\n")

    mhz = output_data.mhz
    ctemps = output_data.ctemps
    watts = output_data.watts
    fans = output_data.fans
    gpus = output_data.gpus
    drives = output_data.drives
    usage = output_data.usage
    mem = output_data.mem
    model_name = output_data.model_name

    lines = []
    lines.append(f"Summary:\nModel: {model_name}\nStart Time: {output_data.time}\n")
    lines.append(f"Runtime: {output_data.run_time}\nCPU: {mhz.get_model()}\n")
    lines.append("Memory SKUs:\n")
    for sku in mem.get_mem_skus():
        lines.append(f"DIMM: {sku}\n")

    mem_type = ''
    mem_data_rows = []
    headers = []
    column_widths = [15, 20, 20, 20]
    justifications = ['<', '>', '>', '>']
    for params in mem:
        if mem_type != params[0]:
            if mem_data_rows:
                append_formatted_section("", mem_data_rows, headers, column_widths, justifications)
                mem_data_rows = []
            mem_type = params[0]
            headers = [mem_type, "Min", "Max", "Mean"]
        mem_data_rows.append([
            mem.get_label(params), mem.get_min(params),
            mem.get_max(params), mem.get_mean(params)
        ])
    append_formatted_section("", mem_data_rows, headers, column_widths, justifications)

    cpu_data_rows = []
    headers = ["Core", "Min %:Mhz", "Max %:Mhz", "Mean %:Mhz"]
    column_widths = [15, 15, 15, 15]
    justifications = ['<', '>', '>', '>']
    for mhz_params, usage_params in zip(mhz, usage):
        cpu_data_rows.append([
            mhz.get_label(mhz_params),
            f"{usage.get_min(usage_params):>4}:{mhz.get_min(mhz_params):>5}",
            f"{usage.get_max(usage_params):>4}:{mhz.get_max(mhz_params):>5}",
            f"{usage.get_mean(usage_params):>4}:{mhz.get_mean(mhz_params):>5}"
        ])
    append_formatted_section("", cpu_data_rows, headers, column_widths, justifications)

    if not ctemps.is_empty():
        ctemps_data_rows = []
        headers = ["Core", "Min C", "Max C", "Mean C"]
        column_widths = [15, 10, 10, 10]
        justifications = ['<', '>', '>', '>']
        for params in ctemps:
            ctemps_data_rows.append([
                ctemps.get_label(params), ctemps.get_min(params),
                ctemps.get_max(params), ctemps.get_mean(params)
            ])
        append_formatted_section("", ctemps_data_rows, headers, column_widths, justifications)

    if not watts.is_empty():
        watts_data_rows = []
        headers = ["CPU", "Min W", "Max W", "Mean W"]
        column_widths = [10, 10, 10, 10]
        justifications = ['<', '>', '>', '>']
        for params in watts:
            watts_data_rows.append([
                watts.get_label(params), watts.get_min(params),
                watts.get_max(params), watts.get_mean(params)
            ])
        append_formatted_section("", watts_data_rows, headers, column_widths, justifications)

    if not fans.is_empty():
        fan_data_rows = []
        driver = ''
        headers = ["Fan", "Current(RPM)", "Min(RPM)", "Max(RPM)", "Mean(RPM)"]
        column_widths = [15, 15, 15, 15, 15]
        justifications = ['<', '>', '>', '>', '>']
        for params in fans:
            if driver != params[0]:
                if fan_data_rows:
                    append_formatted_section(driver, fan_data_rows, headers,
                                             column_widths, justifications)
                    fan_data_rows = []
                driver = params[0]
            fan_data_rows.append([
                fans.get_label(params), fans.get_current(params), fans.get_min(params),
                fans.get_max(params), fans.get_mean(params)
            ])
        append_formatted_section(driver, fan_data_rows, headers, column_widths, justifications)

    if not gpus.is_empty():
        gpu_data_rows = []
        vendor = ''
        name = ''
        headers = ["Data", "Current", "Min", "Max", "Mean"]
        column_widths = [15, 15, 15, 15, 15]
        justifications = ['<', '>', '>', '>', '>']
        for params in gpus:
            driver_version = ""
            if vendor != params[0]:
                if gpu_data_rows:
                    append_formatted_section(f"{vendor}{driver_version}", gpu_data_rows, headers,
                                             column_widths, justifications)
                    gpu_data_rows = []
                vendor = params[0]
                if vendor == 'nvidia':
                    driver_version = " - " + gpus.get_driver_version()
            if name != params[1]:
                name = params[1]
                subsystem = gpus.get_subven(vendor, name)
                subsystem_info = f"SubSystem: {subsystem}" if subsystem else ""
                gpu_data_rows.append([
                    f"GPU: {name}\n{subsystem_info}"
                ])
            if gpus.get_current(params) is not None:
                gpu_data_rows.append([
                    gpus.get_label(params), gpus.get_current(params), gpus.get_min(params),
                    gpus.get_max(params), gpus.get_mean(params)
                ])
        append_formatted_section(f"{vendor}{driver_version}", gpu_data_rows, headers,
                                 column_widths, justifications)

    if not drives.is_empty():
        drive_data_rows = []
        drive = ''
        headers = ["Data", "Current", "Min", "Max", "Mean"]
        column_widths = [15, 15, 15, 15, 15]
        justifications = ['<', '>', '>', '>', '>']
        for params in drives:
            if drive != params[0]:
                if drive_data_rows:
                    append_formatted_section(
                        f"Device: {drive}\nDrive Model: {drives.get_model(drive)}",
                        drive_data_rows, headers, column_widths, justifications
                    )
                    drive_data_rows = []
                drive = params[0]
            if drives.get_current(params) is not None:
                drive_data_rows.append([
                    drives.get_label(params), drives.get_current(params),
                    drives.get_min(params), drives.get_max(params),
                    drives.get_mean(params)
                ])
        append_formatted_section(
            f"Device: {drive}\nDrive Model: {drives.get_model(drive)}",
            drive_data_rows, headers, column_widths, justifications
        )

    with open(file=output_data.summary_fn, mode='w', encoding='utf-8') as outfile:
        outfile.write("".join(lines))
