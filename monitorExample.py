import sys
import xpc
from tkinter import *
import time
from threading import Thread
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk

# Monitors plane's position and controls, updating the display every second
def monitor():
    
    try:

        # Connect to user's instence of X-Plane
        with xpc.XPlaneConnect() as client:

            while True:

                # Get plane's position and controls
                posi = client.getPOSI()
                #ctrl = client.getCTRL()
                airSpeed = client.getDREF("sim/cockpit2/gauges/indicators/airspeed_kts_pilot")

                # Display plane information in a human-readable format
                location_str = f"Latitude: {posi[0]:.4f} Longitude {posi[1]:.4f} Altitude: {posi[2]:.4f} \n\n Pitch: {posi[3]:.4f} Roll {posi[4]:.4f} Yaw: {posi[5]:.4f} Air Speed: {airSpeed}"
                #location_str = f"Latitude: {posi[0]:.4f} Longitude {posi[1]:.4f} Altitude: {posi[2]:.4f} \n\n Pitch: {posi[3]:.4f} Roll {posi[4]:.4f} True Heading: {posi[5]:.4f} Gear {posi[6]:.4f}"
                
                # commented out just in case
                # controls_str = f"Latitudinal Stick: {ctrl[1]:.2f} Longitudinal Stick: {ctrl[0]:.2f} Rudder Pedals: {ctrl[2]:.2f} \n\n Throttle: {ctrl[3]:.2f} Gear: {ctrl[4]:.2f} Flaps: {ctrl[5]:.2f} Speedbrakes: {ctrl[6]:.2f}"

                # Update the display with the new information
                display.update()  
                label.config(text=f"{location_str}\n")
                #label.config(text=f"{location_str}\n\n{controls_str}")

                # Get plane's position and controls
                posi = client.getPOSI()
                #ctrl = client.getCTRL()
                airSpeed = client.getDREF("sim/cockpit2/gauges/indicators/airspeed_kts_pilot")

                # Update position and control metrics
                updateMetrics("Latitude", posi, 0)
                updateMetrics("Longitude", posi, 1)
                updateMetrics("Altitude", posi, 2)
                updateMetrics("Pitch", posi, 3)
                updateMetrics("Roll", posi, 4)
                updateMetrics("AirSpeed", posi, 5)

                # updateMetrics("Latitudinal Stick", ctrl, 1)
                # updateMetrics("Longitudinal Stick", ctrl, 0)
                # updateMetrics("Rudder Pedals", ctrl, 2)
                # updateMetrics("Throttle", ctrl, 3)
                # updateMetrics("Gear", ctrl, 4)
                # updateMetrics("Flaps", ctrl, 5)
                # updateMetrics("Speedbrakes", ctrl, 6)

                updateTime()

                # Update the plots with new data
                createPlot(ax1, "Altitude Over Time", "Altitude", "Altitude")
                createPlot(ax2, "Pitch Over Time", "Pitch", "Pitch")
                createPlot(ax3, "Roll Over Time", "Roll", "Roll")
                createPlot(ax4, "Throttle Over Time", "Throttle", "Throttle")

                # Redraw the canvas 
                canvas.draw()   

                time.sleep(timeInterval)  # Wait for 1 second before the next update 

    except:
        print("Connection lost.")
        display.quit()

# How much data is displayed at a time
metricArraySize = 10

# Initialize passingTime to track time and sampling speed
passingTime = [0.0] * metricArraySize
timeInterval = .5

# Dictionary with all measureable metrics
metrics = {
           "Latitude" : [0.0] * metricArraySize,
           "Longitude" : [0.0] * metricArraySize,
           "Altitude" : [0.0] * metricArraySize,
           "Pitch" : [0.0] * metricArraySize,
           "Roll" : [0.0] * metricArraySize,
           "True Heading" : [0.0] * metricArraySize,
           "Air Speed": [0.0] * metricArraySize
        #    "Gear" : [0.0] * metricArraySize,
        #    "Latitudinal Stick" : [0.0] * metricArraySize,
        #    "Longitudinal Stick" : [0.0] * metricArraySize,
        #    "Rudder Pedals" : [0.0] * metricArraySize,
        #    "Throttle" : [0.0] * metricArraySize,
        #    "Flaps" : [0.0] * metricArraySize,
        #    "Speedbrakes" : [0.0] * metricArraySize
}

textboxValue = 0

# Updates metrics
def updateMetrics(measurement, array, slot):

    # Adds newest measurement to corresponding metric list and removes the oldest
    metrics[measurement].append(array[slot])
    metrics[measurement].pop(0)

# Updates real time as x-axis for graphs
def updateTime():

    passingTime.append(passingTime[-1] + timeInterval)
    passingTime.pop(0)

# Create and update a plot
def createPlot(ax, title, ylabel, measurement):

    ax.clear()
    ax.plot(passingTime, metrics[measurement], label=measurement)
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_xlim(min(passingTime), max(passingTime))
    ax.set_ylabel(ylabel)
    ax.set_ylim(min(metrics[measurement]) - 1, max(metrics[measurement]) + 1)
    

# Gets textbox value
def getTextboxValue():
    textboxValue = textbox.get()
    print(textboxValue)
                 

if __name__ == "__main__":
  
     # Initialize Tkinter display
    display = Tk()
    display.geometry("1000x1200")

    # Create a separate thread to run the monitor function continuously
    monitor_thread = Thread(target=monitor)
    monitor_thread.start()

    # Initialize the matplotlib figure and subplots
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(8, 6))
    fig.tight_layout(pad=3.0)

    # Create initial plots
    createPlot(ax1, "Altitude Over Time", "Altitude", "Altitude")
    createPlot(ax2, "Pitch Over Time", "Pitch", "Pitch")
    createPlot(ax3, "Roll Over Time", "Roll", "Roll")
    createPlot(ax4, "Throttle Over Time", "Throttle", "Throttle")

    # Create the canvas and add it to the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master = display)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    # Create a separate thread to run the monitor function continuously
    monitorThread = Thread(target=monitor)
    #monitorThread.start()

    # 
    selectionOptions = ["Latitude",
                        "Longitude",
                        "Altitude",
                        "Pitch",
                        "Roll",
                        "True Heading",
                        "Latitudinal Stick",
                        "Longitudinal Stick",
                        "Rudder Pedals",
                        "Throttle",
                        "Gear",
                        "Flaps",
                        "Speedbrakes",]
    

    # datatype of menu text 
    dropDown = StringVar() 
    
    # initial menu text 
    dropDown.set(selectionOptions[0]) 
    
    # Create Label 
    label = Label(display, text = " " ) 
    label.pack() 

    # Create Dropdown menu 
    drop = OptionMenu(display, dropDown, *selectionOptions) 
    drop.pack() 

    # Create the combobox
    textbox = ttk.Entry(display)
    textbox.pack()
    
    # Create button, it will change label text 
    button = Button(display, text = "Configure +/-", command = getTextboxValue())
    button.pack() 
    
    # Create Label 
    label = Label(display , text = " ") 
    label.pack()

    display.mainloop()