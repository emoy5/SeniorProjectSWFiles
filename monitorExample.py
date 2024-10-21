# Imports 
import sys
import xpc
from tkinter import *
import time
from threading import Thread, Event
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import csv

# Globals
timeInterval = 0.25  # Sample speed
passingTime = [0.0]  # Time vector for plotting
client = Thread()  # Global client for XPlaneConnect
maneuver = Thread() # Global maneuver for tests
dataLimit = 100  # Limit for data points
stopEvent = Event() # Event to stop the threads
dataFile = 'data.txt' # Where data is stored
csvDataFile = 'data.csv' #storing data into csv file
maneuverStartAltitude = 0.0 # Capture position vector when maneuver is started
maneuverStartHeading = 0.0 # Capture control vector when maneuver is started
maneuverStartAirspeed = 0.0 # Capture airspeed value when maneuver is started
altitudeError = 200.0 # Error range for the altitude (+/-)
headingError = 20.0 # Error range for the heading (+/-)
airspeedError = 10.0 # Error range for the airspeed (+/-)
endManeuverFlag = False # Linked to button to determine when maneuver is over 
targetAltitude = 0 # Altitde the pilot must reach
targetHeading = 0 # Heading the pilot must reach

# Dictionary with all measurable metrics
metrics = {
    # "Time Stamp": [0.0],         #   year-mon-day hour:min:sec
    "Latitude": [0.0],          #	double	n	degrees	The latitude of the aircraft
    "Longitude": [0.0],         #   double	n	degrees	The longitude of the aircraft
    "Altitude": [0.0],          #   double	n	meters	The elevation above MSL of the aircraft
    "Pitch": [0.0],             #   float	y	degrees	The pitch relative to the plane normal to the Y axis in degrees - OpenGL coordinates
    "Roll": [0.0],              #   float	y	degrees	The roll of the aircraft in degrees - OpenGL coordinates
    "True Heading": [0.0],      #   float	y	degrees	The true heading of the aircraft in degrees from the Z axis - OpenGL coordinates
    "Air Speed": [0.0],         #   float	y	knots	Indicated airspeed in knots, pilot. Writeable with override_IAS
    "Vertical Air Speed": [0.0] #	float	y	feet/minute	Indicated vertical speed in feet per minute, pilot system.
}

# Updates metrics as y-axis for graphs
def updateMetrics(measurement, array, slot):
    
    # Add current measurement to that array's metric
    if (measurement == "Altitude"):
        metrics[measurement].append(array[slot]*3.28084) # Altitude is pulled in meters so convert to feet
    else:
        metrics[measurement].append(array[slot])
    
    # Limit data points to the configured limit
    if len(metrics[measurement]) > dataLimit:
        metrics[measurement] = metrics[measurement][-dataLimit:]

# Updates real-time as x-axis for graphs
def updateTime():

    # Adds sampling sleepd to the time vector -- continuous time
    if len(passingTime) == 0:
        passingTime.append(0.0)  # Start with time 0
    else:
        passingTime.append(passingTime[-1] + timeInterval)

# Ensure lengths of passingTime and metric lists are equal before plotting (prevents errors)
def synchronizeLengths():

    # Find the minimum length among passingTime and all metric lists in the metrics dictionary
    minLength = min(len(passingTime), *[len(v) for v in metrics.values()])

    # If passingTime is longer than minLength, truncate it to the last minLength entries.
    if len(passingTime) > minLength:
        passingTime[:] = passingTime[-minLength:]  # Slice passingTime to keep only the last minLength entries.

    # Iterate through each metric in the metrics dictionary.
    for key in metrics.keys():

        # If the length of the current metric list is longer than minLength, truncate it.
        if len(metrics[key]) > minLength:
            metrics[key] = metrics[key][-minLength:]  # Slice the metric list to keep only the last minLength entries.

# Create and update a plot
def createPlot(ax, title, ylabel, measurement):

    ax.clear() # Clear graph

    # Ensure there's data to plot
    if len(passingTime) > 1 and len(metrics[measurement]) > 1:
        ax.plot(passingTime, metrics[measurement], label=measurement)
        #ax.set_xlim(min(passingTime), max(passingTime))  # Dynamically expand x-axis

    # Configure graph
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(ylabel)
    ax.grid(True)

# Monitors plane's position and controls, updating the display every second
def monitor():
    global client, maneuver

    lastUpdateTime = time.perf_counter()  # Track time in seconds

    #Check if the thread was terminated
    while not stopEvent.is_set(): 

        try:

            # Update current time and calculate how much time has passed
            currentTime = time.perf_counter()
            elapsedTime = currentTime - lastUpdateTime

            # Only update metrics/graphs if the interval has passed
            if elapsedTime >= timeInterval:  

                # Get plane's position, calculated airspeed, and vertical airspeed
                position = client.getPOSI()
                airSpeed = client.getDREF("sim/cockpit2/gauges/indicators/airspeed_kts_pilot")
                verticalSpeed = client.getDREF("sim/cockpit2/gauges/indicators/vvi_fpm_pilot")

                # Update position and control metrics
                updateMetrics("Latitude", position, 0)
                updateMetrics("Longitude", position, 1)
                updateMetrics("Altitude", position, 2)
                updateMetrics("Pitch", position, 3)
                updateMetrics("Roll", position, 4)
                updateMetrics("True Heading", position, 5)
                updateMetrics("Air Speed", airSpeed, 0)
                updateMetrics("Vertical Air Speed", verticalSpeed, 0)

                updateTime() # Update time axis
                synchronizeLengths()  # Ensure lists are the same length before plotting
                storeData() # Store updated metrics in a txt file

                # Update the plots with new data
                createPlot(ax1, "Vertical Air Speed", "Vertical Airspeed (ft per min)", "Vertical Air Speed")
                createPlot(ax2, "Position (Latitude)", "Latitude (degrees)", "Latitude")
                createPlot(ax3, "Pitch Rate", "Pitch (degrees)", "Pitch")
                createPlot(ax4, "Yaw Rate", "Heading (degrees)", "True Heading")
                createPlot(ax5, "Air Speed", "Air Speed (kt)", "Air Speed")
                createPlot(ax6, "Position (Longitude)", "Longitude (degrees)", "Longitude")
                createPlot(ax7, "Roll Rate", "Roll (degrees)", "Roll")
                createPlot(ax8, "Altitude", "Altitude (ft above MSL)", "Altitude")

                canvas.draw() # Redraw the canvas 

                lastUpdateTime = currentTime  # Update the last update time

                if(endManeuverFlag == True):
                    endManeuverThread()

        # Log errors and set to disconnected
        except Exception as e:
            print(f"Error in data retrieval: {e}")

            with open(dataFile, "a") as f: 
                f.write("\n--- Server Disconnected ---\n\n")

            with open(csvDataFile, "a") as csvfile:
                newCSVFile = csv.writer(csvfile)
                newCSVFile.writerow(['\n--- Server Disconnected ---\n\n'])

            lbConnectionStatus.set("Disconnected")  # Update the label status
            btnReconnect.config(state=NORMAL)  # Enable reconnect button

            break  # Exit the loop


# Function to reconnect to X-Plane
def reconnect():
    global client, passingTime, metrics, maneuver, endManeuverFlag

    try:

        # Try reconnecting to the X-Plane server
        client = xpc.XPlaneConnect()
        lbConnectionStatus.set("Connected")  # Update label to connected
        btnReconnect.config(state=DISABLED)  # Disable reconnect button

        # Reset metrics and passingTime
        passingTime = [0.0]  # Reset time
        for key in metrics.keys():
            metrics[key] = [0.0]  # Reset metrics to starting values

        endManeuverFlag = True
        lbManeuverStatus.set("Maneuver Status: Not Started")       
        btnEndManeuver.config(state=DISABLED)
        enableManeuverButtons()
        endManeuverThread()

        # Start the monitor thread again
        startMonitorThread()

    except Exception as e:
        print(f"Failed to reconnect: {e}")
        lbConnectionStatus.set("Disconnected")
        btnReconnect.config(state=NORMAL)  # Enable reconnect button on failure

# Starts the monitor function in a separate thread
def startMonitorThread():
    global monitorThread

    # Thread runs if stop event isn't called
    if not stopEvent.is_set():
        monitorThread = Thread(target=monitor, daemon=True)
        monitorThread.start()

# Handler for window close event
def onClosing():
    global monitorThread, maneuver

    stopEvent.set()  # Set the stop event to terminate threads

    # Check if the monitor thread is still running
    if monitorThread.is_alive():  
        monitorThread.join(timeout=1)  # Wait for 5 seconds instead of 1
        if monitorThread.is_alive():
            print("Warning: Monitor thread did not finish in time. Terminating forcefully.")
            monitorThread = None  # Set monitorThread to None after termination

    # Check if the maneuver thread is still running
    endManeuverThread()

    # Close the text file and add a partition line
    with open(dataFile, "a") as f:  # Open the file in append mode
        f.write("\n--- End of Session ---\n\n")  # Add a partition line
    
    with open(csvDataFile, "w", newline='') as csvFile:  # Open the file in append mode
        newCSVFile = csv.writer(csvFile)  
        newCSVFile.writerow('\n--- End of Session ---\n\n') # Add a partition line

    display.quit()  # Close the Tkinter window
    os._exit(0)  # Forcefully terminate the process

def storeData():
    # Check if the file exists to determine if we need to write the header
    file_exists = os.path.isfile(dataFile)
    file_exists1 = os.path.isfile(csvDataFile)

    with open(dataFile, 'a') as file:  # Open in append mode
        # Write header only if the file is new
        if not file_exists:
            header = "Timestamp," + ",".join(metrics.keys()) + "\n"
            file.write(header)

        # Write a timestamp for the current data entry
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        # Collect the latest values in the same order as the header
        latest_values = [metrics[metric][-1] for metric in metrics.keys()]
        # Create a row for the data
        data_row = f"{timestamp}," + ",".join(map(str, latest_values)) + "\n"
        file.write(data_row)  # Append the data row to the file

    with open(csvDataFile, "a", newline= '') as csvFile:  # Open the file in write mode
        newCSVFile = csv.writer(csvFile)
        
        if not file_exists1:
            header = ['Timestamp'] + list(metrics.keys())
            newCSVFile.writerow(header)
       
        # Write a timestamp for the current data entry
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        row = [timestamp] + [metrics[metric][-1] for metric in metrics.keys()] # combine timestamp and metric values
        newCSVFile.writerow(row)  # Append the data row to the file
        
    print(f"Data written to {csvDataFile}")
# Ends maneuver test
def toggleManeuver():
    global endManeuverFlag

    endManeuverFlag = not endManeuverFlag

def enableManeuverButtons():
    btnConstantClimbs.config(state=NORMAL)
    btnConstantDescents.config(state=NORMAL)
    btnStraightFlight.config(state=NORMAL)
    btnTurnsToHeadings.config(state=NORMAL)

def disableManeuverButtons():
    btnConstantClimbs.config(state=DISABLED)
    btnConstantDescents.config(state=DISABLED)
    btnStraightFlight.config(state=DISABLED)
    btnTurnsToHeadings.config(state=DISABLED)

def endManeuverThread():
    # Check if the maneuver thread is still running
    if maneuver.is_alive():  
        maneuver.join(timeout=1)  # Wait for 1 second
        if maneuver.is_alive():
            print("Warning: Maneuver thread did not finish in time.")

# Initiate straight and level flight thread
def straightAndLevel():
    global maneuver, maneuverStartAltitude, maneuverStartHeading, maneuverStartAirspeed, endManeuverFlag

    try:

        # Document that the test is initaited
        with open(dataFile, "a") as f: 
            f.write("\n--- Straight-and-Level Flight ---\n\n") 
        
        with open(csvDataFile, "w", newline='') as csvfile: 
            newCSVFile = csv.writer(csvfile)
            newCSVFile.writerow(['\n--- Straight-and-Level Flight ---\n\n']) 

        lbManeuverStatus.set("Maneuver Status: Straight-and-Level Flight Initiated") 

        endManeuverFlag = False

        # Capture initial values
        maneuverStartAltitude = metrics["Altitude"][-1]
        maneuverStartHeading = metrics["True Heading"][-1]
        maneuverStartAirspeed = metrics["Air Speed"][-1]

        # Thread runs if stop event isn't called
        if not stopEvent.is_set():
            maneuver = Thread(target=performStraightAndLevel, daemon=True)
            maneuver.start()
            
    except Exception as e:
        print(f"Error in Straight-and-Level Flight: {e}")

# Evaluates straight and level maneuver
def performStraightAndLevel():
    global maneuver, endManeuverFlag
    btnEndManeuver.config(state=NORMAL)
    disableManeuverButtons()
    failed = False

    try:
        # Continuous check for altitude until maneuver is stopped
        while not stopEvent.is_set():
            # Ends maneuver manually
            if (endManeuverFlag == True):
                break

            currentAltitude = metrics["Altitude"][-1]
            currentHeading =  metrics["True Heading"][-1]
            currentAirspeed = metrics["Air Speed"][-1]

            # Check altitude error range
            if (currentAltitude > maneuverStartAltitude + altitudeError or
                currentAltitude < maneuverStartAltitude - altitudeError):
                lbManeuverStatus.set("Maneuver Status: Straight-and-Level Flight Maneuver failed (Altitude)")  
                failed = True
                break  # Exit the loop if the altitude is not maintained

            # Check heading error range
            if (currentHeading > maneuverStartHeading + headingError or
                currentHeading < maneuverStartHeading - headingError):
                lbManeuverStatus.set("Maneuver Status: Straight-and-Level Flight Maneuver failed (Heading)")  
                failed = True
                break  # Exit the loop if the altitude is not maintained

            # Check airspeed error range
            if (currentAirspeed > maneuverStartAirspeed + airspeedError or
                currentAirspeed < maneuverStartAirspeed - airspeedError):
                lbManeuverStatus.set("Maneuver Status: Straight-and-Level Flight Maneuver failed (Airspeed)")  
                failed = True
                break  # Exit the loop if the altitude is not maintained

            time.sleep(timeInterval)  # Allow monitor thread to run smoothly
            
    except Exception as e:
        print(f"Error in evaluating Straight-and-Level Flight: {e}")

    finally:
                
        if(not failed):
            lbManeuverStatus.set("Maneuver Status: Straight-and-Level Flight Maneuver Passed") 

            with open(dataFile, "a") as f: 
                f.write("\n--- Straight-and-Level Flight Ended (Passed) ---\n\n")
        
        else:
            with open(dataFile, "a") as f: 
                f.write("\n--- Straight-and-Level Flight Ended (Failed) ---\n\n")

        endManeuverFlag = False
        btnEndManeuver.config(state=DISABLED)
        enableManeuverButtons()

# Initiate constant climbs thread
def constantClimbs():
    global maneuver, maneuverStartAltitude, maneuverStartHeading, maneuverStartAirspeed, targetAltitude, endManeuverFlag

    try:

        # Capture initial values
        maneuverStartAltitude = metrics["Altitude"][-1]
        maneuverStartHeading = metrics["True Heading"][-1]
        maneuverStartAirspeed = metrics["Air Speed"][-1]

        endManeuverFlag = False 

        try:
            targetAltitude = float(entryTargetAltitude.get())

            if(targetAltitude < maneuverStartAltitude):

                print("Invalid input for target altitude")
                return

        except ValueError:
            print("Invalid input for target altitude")
            return

        # Document that the test is initiated
        with open(dataFile, "a") as f:
            f.write("\n--- Constant Airspeed Climbs ---\n\n")

        lbManeuverStatus.set("Maneuver Status: Constant Airspeed Climbs Initiated")

        # Thread runs if stop event isn't called
        if not stopEvent.is_set():
            maneuver = Thread(target=performConstantClimbs, daemon=True)
            maneuver.start()

    except Exception as e:
        print(f"Error in Constant Airspeed Climbs: {e}")

# Evaluates constant airspeed climbs
def performConstantClimbs():
    global maneuver, endManeuverFlag
    btnEndManeuver.config(state=NORMAL)
    disableManeuverButtons()
    failed = False

    try:
        # Continuous check for altitude until maneuver is stopped
        while not stopEvent.is_set():
            # Ends maneuver manually -- test ended before pilot reached altitude
            if endManeuverFlag:
                failed = True
                lbManeuverStatus.set("Maneuver Status: Constant Airspeed Climbs Failed (Aborted)")
                break

            currentAltitude = metrics["Altitude"][-1]
            currentHeading = metrics["True Heading"][-1]
            currentAirspeed = metrics["Air Speed"][-1]

            # Check if the plane leveled off within the altitude error range
            if (targetAltitude - altitudeError <= currentAltitude <= targetAltitude + altitudeError):
                lbManeuverStatus.set("Maneuver Status: Constant Airspeed Climbs Passed")

                # End the climb when target altitude is reached
                break

            # Check heading error range
            if (currentHeading > maneuverStartHeading + headingError or
                currentHeading < maneuverStartHeading - headingError):
                lbManeuverStatus.set("Maneuver Status: Constant Airspeed Climbs Failed (Heading)")
                failed = True
                break

            # Check airspeed error range
            if (currentAirspeed > maneuverStartAirspeed + airspeedError or
                currentAirspeed < maneuverStartAirspeed - airspeedError):
                lbManeuverStatus.set("Maneuver Status: Constant Airspeed Climbs Failed (Airspeed)")
                failed = True
                break

            time.sleep(timeInterval)  # Allow monitor thread to run smoothly

    except Exception as e:
        print(f"Error in evaluating Constant Airspeed Climbs: {e}")

    finally:
        if not failed:
            lbManeuverStatus.set("Maneuver Status: Constant Airspeed Climbs Passed")
            with open(dataFile, "a") as f:
                f.write("\n--- Constant Airspeed Climbs Ended (Passed) ---\n\n")
        else:
            with open(dataFile, "a") as f:
                f.write("\n--- Constant Airspeed Climbs Ended (Failed) ---\n\n")

        endManeuverFlag = False
        btnEndManeuver.config(state=DISABLED)
        enableManeuverButtons()

# Initiate constant desc thread
def constantDescents():
    
    global maneuver, maneuverStartAltitude, maneuverStartHeading, maneuverStartAirspeed, targetAltitude, endManeuverFlag

    try:

        # Capture initial values
        maneuverStartAltitude = metrics["Altitude"][-1]
        maneuverStartHeading = metrics["True Heading"][-1]
        maneuverStartAirspeed = metrics["Air Speed"][-1]

        endManeuverFlag = False 

        try:
            targetAltitude = float(entryTargetAltitude.get())

            if(targetAltitude > maneuverStartAltitude):

                print("Invalid input for target altitude")
                return

        except ValueError:
            print("Invalid input for target altitude")
            return

        # Document that the test is initiated
        with open(dataFile, "a") as f:
            f.write("\n--- Constant Airspeed Descents ---\n\n")

        lbManeuverStatus.set("Maneuver Status: Constant Airspeed Descents Initiated")

        # Thread runs if stop event isn't called
        if not stopEvent.is_set():
            maneuver = Thread(target=performConstantDescents, daemon=True)
            maneuver.start()

    except Exception as e:
        print(f"Error in Constant Airspeed Descents: {e}")

# Evaluates constant airspeed descents
def performConstantDescents():
    global maneuver, endManeuverFlag
    btnEndManeuver.config(state=NORMAL)
    disableManeuverButtons()
    failed = False

    try:
        # Continuous check for altitude until maneuver is stopped
        while not stopEvent.is_set():
            # Ends maneuver manually -- test ended before pilot reached altitude
            if endManeuverFlag:
                failed = True
                lbManeuverStatus.set("Maneuver Status: Constant Airspeed Descents Failed (Aborted)")
                break

            currentAltitude = metrics["Altitude"][-1]
            currentHeading = metrics["True Heading"][-1]
            currentAirspeed = metrics["Air Speed"][-1]

            # Check if the plane leveled off within the altitude error range
            if (targetAltitude + altitudeError <= currentAltitude <= targetAltitude - altitudeError):
                lbManeuverStatus.set("Maneuver Status: Constant Airspeed Descents Passed")

                # End the climb when target altitude is reached
                break

            # Check heading error range
            if (currentHeading > maneuverStartHeading + headingError or
                currentHeading < maneuverStartHeading - headingError):
                lbManeuverStatus.set("Maneuver Status: Constant Airspeed Descents Failed (Heading)")
                failed = True
                break

            # Check airspeed error range
            if (currentAirspeed > maneuverStartAirspeed + airspeedError or
                currentAirspeed < maneuverStartAirspeed - airspeedError):
                lbManeuverStatus.set("Maneuver Status: Constant Airspeed Descents Failed (Airspeed)")
                failed = True
                break

            time.sleep(timeInterval)  # Allow monitor thread to run smoothly

    except Exception as e:
        print(f"Error in evaluating Constant Airspeed Descents: {e}")

    finally:
        if not failed:
            lbManeuverStatus.set("Maneuver Status: Constant Airspeed Descents Passed")
            with open(dataFile, "a") as f:
                f.write("\n--- Constant Airspeed Descents Ended (Passed) ---\n\n")
        else:
            with open(dataFile, "a") as f:
                f.write("\n--- Constant Airspeed Descents Ended (Failed) ---\n\n")

        endManeuverFlag = False
        btnEndManeuver.config(state=DISABLED)
        enableManeuverButtons()

# Initiate turns to heading thread
def turnsToHeadings():
    global maneuver, maneuverStartAltitude, maneuverStartHeading, maneuverStartAirspeed, targetHeading, endManeuverFlag

    try:

        # Capture initial values
        maneuverStartAltitude = metrics["Altitude"][-1]
        maneuverStartHeading = metrics["True Heading"][-1]
        maneuverStartAirspeed = metrics["Air Speed"][-1]

        endManeuverFlag = False 

        try:
            targetHeading = float(entryTargetHeading.get())

            if(360 < targetHeading or targetHeading < 0):

                print("Invalid input for target heading")
                return

        except ValueError:
            print("Invalid input for target heading")
            return

        # Document that the test is initiated
        with open(dataFile, "a") as f:
            f.write("\n--- Turns to Headings ---\n\n")

        lbManeuverStatus.set("Maneuver Status: Turns to Headings Initiated")

        # Thread runs if stop event isn't called
        if not stopEvent.is_set():
            maneuver = Thread(target=performTurnsToHeadings, daemon=True)
            maneuver.start()

    except Exception as e:
        print(f"Error in Turns to Headings: {e}")

# Evaluates turns to headings
def performTurnsToHeadings():
    global maneuver, endManeuverFlag
    btnEndManeuver.config(state=NORMAL)
    disableManeuverButtons()
    failed = False

    try:
        # Continuous check for heading until maneuver is stopped
        while not stopEvent.is_set():
            # Ends maneuver manually -- test ended before pilot reached altitude
            if endManeuverFlag:
                failed = True
                lbManeuverStatus.set("Maneuver Status: Turns to Headings Failed (Aborted)")
                break

            currentAltitude = metrics["Altitude"][-1]
            currentHeading = metrics["True Heading"][-1]
            currentAirspeed = metrics["Air Speed"][-1]

            # Check altitude error range
            if (currentAltitude > maneuverStartAltitude + altitudeError or
                currentAltitude < maneuverStartAltitude - altitudeError):
                lbManeuverStatus.set("Maneuver Status: Turns to Headings failed (Altitude)")  
                failed = True
                break  # Exit the loop if the altitude is not maintained

            # Check if the plane heading is within range
            if (is_heading_in_range(currentHeading, targetHeading, headingError)):
                lbManeuverStatus.set("Maneuver Status: Turns to Headings Passed")

                # End the climb when target altitude is reached
                break

            # Check airspeed error range
            if (currentAirspeed > maneuverStartAirspeed + airspeedError or
                currentAirspeed < maneuverStartAirspeed - airspeedError):
                lbManeuverStatus.set("Maneuver Status: Turns to Headings Failed (Airspeed)")
                failed = True
                break

            time.sleep(timeInterval)  # Allow monitor thread to run smoothly

    except Exception as e:
        print(f"Error in evaluating Turns to Headings: {e}")

    finally:
        if not failed:
            lbManeuverStatus.set("Maneuver Status: Turns to Headings Passed")
            with open(dataFile, "a") as f:
                f.write("\n--- Turns to Headings Ended (Passed) ---\n\n")
        else:
            with open(dataFile, "a") as f:
                f.write("\n--- Turns to Headings Ended (Failed) ---\n\n")

        endManeuverFlag = False
        btnEndManeuver.config(state=DISABLED)
        enableManeuverButtons()

def is_heading_in_range(currentHeading, targetHeading, headingError):
    # Normalize both headings to the range [0, 360)
    normalized_current = currentHeading % 360
    normalized_target = targetHeading % 360

    # Calculate the shortest difference between headings
    diff = (normalized_target - normalized_current + 360) % 360

    # Check if within the headingError, either clockwise or counterclockwise
    result = min(diff, 360 - diff) <= headingError

    return result

if __name__ == "__main__":

    # Initialize Tkinter display
    display = Tk()
    display.geometry("1920x1080")

    # Set the window close event handler
    display.protocol("WM_DELETE_WINDOW", onClosing)

    # Initialize the matplotlib figure and subplots
    fig, ((ax1, ax2, ax3, ax4), (ax5, ax6, ax7, ax8)) = plt.subplots(2, 4, figsize=(16, 6))
    fig.suptitle('Instructor Panel')
    fig.tight_layout(pad=3.0)

    # Create initial plots
    createPlot(ax1, "Vertical Air Speed", "Vertical Airspeed (ft per min)", "Vertical Air Speed")
    createPlot(ax2, "Position (Latitude)", "Latitude (degrees)", "Latitude")
    createPlot(ax3, "Pitch Rate", "Pitch (degrees)", "Pitch")
    createPlot(ax4, "Yaw Rate", "Heading (degrees)", "True Heading")
    createPlot(ax5, "Air Speed", "Air Speed (kt)", "Air Speed")
    createPlot(ax6, "Position (Longitude)", "Longitude (degrees)", "Longitude")
    createPlot(ax7, "Roll Rate", "Roll (degrees)", "Roll")
    createPlot(ax8, "Altitude", "Altitude (ft above MSL)", "Altitude")

    # Create the canvas and add it to the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=display)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    # Label to show the connection status
    lbConnectionStatus = StringVar()
    lbConnectionStatus.set("Disconnected")  # Initially set to disconnected
    lbStatus = Label(display, textvariable=lbConnectionStatus, font=("Arial", 14))
    lbStatus.pack(pady=10)

    # Reconnect button
    btnReconnect = Button(display, text="Reconnect", command=reconnect, state=NORMAL)
    btnReconnect.pack(pady=10)

    # Buttons to correspond with maneuvers
    btnStraightFlight = Button(display, text="Straight-and-Level Flight", command=straightAndLevel, state=NORMAL)
    btnStraightFlight.pack()

    btnConstantClimbs = Button(display, text="Constant Airspeed Climbs", command=constantClimbs, state=NORMAL)
    btnConstantClimbs.pack()

    btnConstantDescents = Button(display, text="Constant Airspeed Descents", command=constantDescents, state=NORMAL)
    btnConstantDescents.pack()

    btnTurnsToHeadings = Button(display, text="Turns to Headings", command=turnsToHeadings, state=NORMAL)
    btnTurnsToHeadings.pack()

    # input field for target altitude
    lbAltitudeEntry = Label(display, text="Set Target Altitude (ft):", font=("Arial", 14))
    lbAltitudeEntry.pack(pady=10)
    entryTargetAltitude = Entry(display)
    entryTargetAltitude.pack(pady=10)

    # input field for target heading
    lbHeadingEntry = Label(display, text="Set Target Heading (degrees):", font=("Arial", 14))
    lbHeadingEntry.pack(pady=10)
    entryTargetHeading = Entry(display)
    entryTargetHeading.pack(pady=10)

    # End Maneuver button
    btnEndManeuver = Button(display, text="End Maneuver", command=toggleManeuver, state=DISABLED)
    btnEndManeuver.pack(pady=10)

    # Maneuver status
    lbManeuverStatus = StringVar()
    lbManeuverStatus.set("Maneuver Status: Not Started")  # Initial status
    lblManeuverStatus = Label(display, textvariable=lbManeuverStatus, font=("Arial", 14))
    lblManeuverStatus.pack(pady=10)

    # Start the initial connection and monitor thread
    reconnect()
    
    # Start the Tkinter main loop
    display.mainloop()