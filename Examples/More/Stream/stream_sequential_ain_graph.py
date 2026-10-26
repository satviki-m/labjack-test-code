"""
Demonstrates how to stream a range of sequential analog inputs using the
eStream functions. Useful when streaming many analog inputs. AIN channel scan
list is FIRST_AIN_CHANNEL to FIRST_AIN_CHANNEL + NUMBER_OF_AINS - 1.

This version also plots every streamed data point live with matplotlib, one
subplot per AIN channel. The plot updates after each eStreamRead and stays open
after the stream finishes. Close the window or press Ctrl+C to stop early.

Relevant Documentation:

LJM Library:
    LJM Library Installer:
        https://labjack.com/support/software/installers/ljm
    LJM Users Guide:
        https://labjack.com/support/software/api/ljm
    Opening and Closing:
        https://labjack.com/support/software/api/ljm/function-reference/opening-and-closing
    NamesToAddresses:
        https://labjack.com/support/software/api/ljm/function-reference/utility/ljmnamestoaddresses
    eWriteName:
        https://labjack.com/support/software/api/ljm/function-reference/ljmewritename
    eWriteNames:
        https://labjack.com/support/software/api/ljm/function-reference/ljmewritenames
    Stream Functions (such as eStreamRead, eStreamStart and eStreamStop):
        https://labjack.com/support/software/api/ljm/function-reference/stream-functions
   
T-Series and I/O:
    Modbus Map:
        https://labjack.com/support/software/api/modbus/modbus-map
    Stream Mode:
        https://labjack.com/support/datasheets/t-series/communication/stream-mode
    Analog Inputs:
        https://labjack.com/support/datasheets/t-series/ain
    Digital I/O:
        https://labjack.com/support/datasheets/t-series/digital-io

Note:
    Our Python interfaces throw exceptions when there are any issues with
    device communications that need addressed. Many of our examples will
    terminate immediately when an exception is thrown. The onus is on the API
    user to address the cause of any exceptions thrown, and add exception
    handling when appropriate. We create our own exception classes that are
    derived from the built-in Python Exception class and can be caught as such.
    For more information, see the implementation in our source code and the
    Python standard documentation.
"""
from datetime import datetime
import math
import sys

import matplotlib.pyplot as plt
from labjack import ljm


MAX_REQUESTS = 30  # The number of eStreamRead calls that will be performed.
FIRST_AIN_CHANNEL = 0  # 0 = AIN0
NUMBER_OF_AINS = 8
SHUNT_OHMS = 0.1  # Current sense resistor: current (A) = volts / SHUNT_OHMS

# Fixed-order line colors, one per channel (wraps after 8 channels).
CHANNEL_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                  "#e87ba4", "#008300", "#4a3aa7", "#e34948"]


def setup_plot(channelNames):
    """Create one subplot per channel, sharing the time axis."""
    plt.ion()
    numCh = len(channelNames)
    cols = 2 if numCh > 1 else 1
    rows = int(math.ceil(numCh / float(cols)))
    fig, axes = plt.subplots(rows, cols, sharex=True, squeeze=False,
                             figsize=(12, 2.0 * rows + 1))
    axes = axes.flatten()
    lines = []
    for j, name in enumerate(channelNames):
        ax = axes[j]
        line, = ax.plot([], [], linewidth=1.0,
                        color=CHANNEL_COLORS[j % len(CHANNEL_COLORS)])
        ax.set_title(name, fontsize=10, loc="left")
        ax.set_ylabel("V")
        ax.grid(True, color="#dddddd", linewidth=0.5)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        lines.append(line)
    # Hide unused subplots when the channel count is odd.
    for ax in axes[numCh:]:
        ax.set_visible(False)
    for ax in axes[max(0, numCh - cols):numCh]:
        ax.set_xlabel("Time (s)")
    fig.suptitle("Live stream: all data points")
    fig.tight_layout()
    plt.show(block=False)
    return fig, axes[:numCh], lines


def update_plot(fig, axes, lines, times, channelData, title):
    """Redraw every line with all data collected so far."""
    for ax, line, data in zip(axes, lines, channelData):
        line.set_data(times, data)
        ax.relim()
        ax.autoscale_view()
    fig.suptitle(title)
    fig.canvas.draw_idle()
    fig.canvas.flush_events()
    plt.pause(0.001)

# Open first found LabJack
handle = ljm.openS("ANY", "ANY", "ANY")  # Any device, Any connection, Any identifier
#handle = ljm.openS("T8", "ANY", "ANY")  # T8 device, Any connection, Any identifier
#handle = ljm.openS("T7", "ANY", "ANY")  # T7 device, Any connection, Any identifier
#handle = ljm.openS("T4", "ANY", "ANY")  # T4 device, Any connection, Any identifier
#handle = ljm.open(ljm.constants.dtANY, ljm.constants.ctANY, "ANY")  # Any device, Any connection, Any identifier

info = ljm.getHandleInfo(handle)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

deviceType = info[0]

# Filled in during the stream; used for the final averages.
aScanListNames = []
channelData = []

try:
    # When streaming, negative channels and ranges can be configured for
    # individual analog inputs, but the stream has only one settling time and
    # resolution.
    ljm.eWriteName(handle, "AIN0_RANGE", 10.0)

    if deviceType == ljm.constants.dtT4:
        # T4 configuration

        # Configure the channels to analog input or digital I/O.
        # Update all digital I/O channels. b1 = Ignored. b0 = Affected.
        dioInhibit = 0x00000  # b00000000000000000000
        # Set AIN0-AIN3 and AIN FIRST_AIN_CHANNEL to
        # FIRST_AIN_CHANNEL+NUMBER_OF_AINS-1 as analog inputs (b1), the rest as
        # digital I/O (b0).
        dioAnalogEnable = (((2 ** NUMBER_OF_AINS) - 1) << FIRST_AIN_CHANNEL) | 0xF
        ljm.eWriteNames(handle, 2,
                        ["DIO_INHIBIT", "DIO_ANALOG_ENABLE"],
                        [dioInhibit, dioAnalogEnable])

        # Configure the stream settling times and stream resolution index.
        aNames = ["STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
        aValues = [0, 0]  # 0 (default), 0 (default)
        ljm.eWriteNames(handle, len(aNames), aNames, aValues)


    else:
        # LabJack T7 and T8 configuration

        # Ensure triggered stream is disabled.
        ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)
        # Enabling internally-clocked stream.
        ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)

        # AIN ranges are +/-10 V (T7) or +/-11 V (T8).
        # Stream resolution index is 0 (default).
        aNames = ["AIN_ALL_RANGE", "STREAM_RESOLUTION_INDEX"]
        aValues = [10.0, 0]


        # Negative channel and settling configurations do not apply to the T8
        if deviceType == ljm.constants.dtT7:
            #     Negative Channel = GND (single ended)
            #     Settling = 0 (auto)
            aNames.extend(["AIN_ALL_NEGATIVE_CH", "STREAM_SETTLING_US"])
            aValues.extend([ljm.constants.GND, 0])

    # Stream configuration
    aScanListNames = ["AIN%i" % i for i in range(FIRST_AIN_CHANNEL, FIRST_AIN_CHANNEL + NUMBER_OF_AINS)]  # Scan list names
    print("\nScan List = " + " ".join(aScanListNames))
    numAddresses = len(aScanListNames)
    aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
    scanRate = 1000
    scansPerRead = int(scanRate / 2)

    # Configure and start stream
    scanRate = ljm.eStreamStart(handle, scansPerRead, numAddresses, aScanList, scanRate)
    print("\nStream started with a scan rae of %0.0f Hz." % scanRate)

    # Live plot setup. All data points for every channel are kept so the
    # whole stream is plotted.
    fig, axes, lines = setup_plot(aScanListNames)
    times = []
    channelData = [[] for _ in range(numAddresses)]
    sampleIndex = 0

    print("\nPerforming %i stream reads." % MAX_REQUESTS)
    start = datetime.now()
    totScans = 0
    totSkip = 0  # Total skipped samples

    # def rand_solenoid(probability):
    #     if random.random() < probability:
    #         ljm.eWriteName(handle, "FIO0", 1)

    i = 1

    while i <= MAX_REQUESTS:
        ret = ljm.eStreamRead(handle)

        #rand_solenoid(0.2)

        aData = ret[0]
        scans = len(aData) / numAddresses
        totScans += scans

        # Count the skipped samples which are indicated by -9999 values. Missed
        # samples occur after a device's stream buffer overflows and are
        # reported after auto-recover mode ends.
        curSkip = aData.count(-9999.0)
        totSkip += curSkip

        print("\neStreamRead %i" % i)
        ainStr = ""
        for j in range(0, numAddresses):
            aData[j] = aData[j]# / 5.9 * 1000 / 51.0
            a_conversion = aData[j] / 1.4 * 1000.0 # mA
             
            ainStr += "%s = %0.5f, %0.5f " % (aScanListNames[j], aData[j], a_conversion)
        print("  1st scan out of %i: %s" % (scans, ainStr))
        print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
              "%i" % (curSkip / numAddresses, ret[1], ret[2]))
        print(i)

        # Deinterleave the scans (ch0, ch1, ..., chN, ch0, ...) and add them
        # to the plot data. Skipped samples (-9999) are plotted as gaps.
        numScans = int(scans)
        for s in range(numScans):
            times.append((sampleIndex + s) / scanRate)
        sampleIndex += numScans
        for j in range(numAddresses):
            for v in aData[j::numAddresses]:
                channelData[j].append(float("nan") if v == -9999.0 else v)

        if not plt.fignum_exists(fig.number):
            print("\nPlot window closed, stopping stream.")
            break
        update_plot(fig, axes, lines, times, channelData,
                    "Live stream: eStreamRead %i of %i, %i scans per channel"
                    % (i, MAX_REQUESTS, sampleIndex))
        i += 1

    end = datetime.now()

    print("\nTotal scans = %i" % (totScans))
    tt = (end - start).seconds + float((end - start).microseconds) / 1000000
    print("Time taken = %f seconds" % (tt))
    print("LJM Scan Rate = %f scans/second" % (scanRate))
    print("Timed Scan Rate = %f scans/second" % (totScans / tt))
    print("Timed Sample Rate = %f samples/second" % (totScans * numAddresses / tt))
    print("Skipped scans = %0.0f" % (totSkip / numAddresses))
except KeyboardInterrupt:
    print("\nInterrupted by user.")
except ljm.LJMError:
    ljme = sys.exc_info()[1]
    print(ljme)
except Exception:
    e = sys.exc_info()[1]
    print(e)

try:
    print("\nStop Stream")
    ljm.eStreamStop(handle)
except ljm.LJMError:
    ljme = sys.exc_info()[1]
    print(ljme)
except Exception:
    e = sys.exc_info()[1]
    print(e)

# Close handle
ljm.close(handle)

# Final average of all valid (non-skipped) data points per channel.
if channelData and any(channelData):
    print("\nFinal averages over all data points:")
    for j, name in enumerate(aScanListNames):
        valid = [v for v in channelData[j] if not math.isnan(v)]
        if not valid:
            print("  %s: no valid samples" % name)
            continue
        avg = sum(valid) / len(valid)  # volts
        avgAmps = avg / SHUNT_OHMS
        print("  %s = %0.5f V -> %0.6f A, %0.5f mA  (%i samples)"
              % (name, avg, avgAmps, avgAmps * 1000.0, len(valid)))
        if plt.fignum_exists(fig.number):
            axes[j].axhline(avg, color="#888888", linewidth=1.0,
                            linestyle="--")
            axes[j].set_title("%s   avg = %0.5f V (%0.5f mA)"
                              % (name, avg, avgAmps * 1000.0),
                              fontsize=10, loc="left")
    if plt.fignum_exists(fig.number):
        fig.canvas.draw_idle()

# Keep the final plot open until the user closes the window.
if plt.get_fignums():
    print("\nClose the plot window to exit.")
    plt.ioff()
    plt.show()
