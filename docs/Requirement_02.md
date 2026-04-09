### OT ENVIRONMENT MONITORING SYSTEM
## Real-Time Air Quality & Climate Monitoring Device

1. Project Overview
The OT Environment Monitoring System is a real-time embedded device designed to continuously monitor indoor air quality and environmental parameters in Occupational Therapy (OT) settings, medical rooms, labs, and sensitive work environments. The system uses industry-standard sensors connected to a Raspberry Pi microprocessor to capture, process, and display live environmental data on a local dashboard. 

The device monitors the following parameters:
•	Particulate Matter: PM1.0, PM2.5, PM10 (via PMS5003 sensor), Research on this for better clarification, what are the criteria according to the best case.
•	Temperature and Relative Humidity (via BME280 sensor), Research on this for better clarification, how to use in the medical sector.
•	Barometric Pressure (via BME280 sensor)
•	CO2 Gas Concentration (via MH-Z19 or similar CO2 sensor)
•	Differential Pressure (via pressure difference sensor)

The system evaluates all sensor readings against established medical and environmental criteria and displays color-coded status indicators: Excellent, Good, or Warning — providing instant visual feedback to room occupants and clinical staff.

2. Project Objectives
1.	Design a compact, real-time environmental monitoring device for OT and medical environments.
2.	Integrate multiple sensors (BME280, PMS5003, CO2, Pressure Difference, etc) with Raspberry Pi.
3.	Process and display sensor data on a live dashboard on a connected screen.
4.	Evaluate sensor readings against medical air quality standards (WHO, ASHRAE, OSHA).
5.	Alert users with Excellent / Good / Warning status indicators based on real-time readings.
6.	Enable data logging for historical analysis and compliance reporting.

3. Hardware Components
The following components are choosed for the OT Environment Monitoring System: 

S.No	Component	Purpose	Interface
1	Raspberry Pi 4 Model B	Main processing unit, runs dashboard software	GPIO, I2C, UART, USB
2	BME280 Sensor	Temperature, Humidity, Atmospheric Pressure	I2C (0x76 or 0x77)
3	PMS5003 Sensor	PM1.0, PM2.5, PM10 particulate matter detection	UART (TX/RX Serial)
4	MH-Z19B CO2 Sensor	Carbon dioxide concentration in ppm	UART or PWM
5	Differential Pressure Sensor	Air pressure difference between two points	I2C / Analog via ADC
6	7-inch Touchscreen Display	Displays real-time dashboard with sensor readings	HDMI / DSI
7	MicroSD Card (32GB)	OS, software, and data logging storage	MicroSD Slot
8	5V / 3A Power Supply	Power for Raspberry Pi and peripherals	USB-C
9	Jumper Wires & Breadboard	Prototyping connections between components	GPIO Pins
10	Enclosure / Housing Box	Protects components, provides ventilation holes	Physical Mount

Be Sure to give suggestion of the choices above made whether it is good, best or the project.

4. Sensor Descriptions
4.1 BME280 — Temperature, Humidity & Pressure Sensor
The BME280 is a highly accurate MEMS (Micro-Electro-Mechanical Systems) sensor from Bosch Sensortec. It measures three critical environmental parameters in a single compact package and communicates via I2C protocol.

•	Temperature Range: -40 degrees C to +85 degrees C | Accuracy: +/- 1.0 degrees C
•	Humidity Range: 0 to 100% RH | Accuracy: +/- 3% RH
•	Pressure Range: 300 to 1100 hPa | Accuracy: +/- 1 hPa
•	Communication Protocol: I2C (primary) or SPI
•	Operating Voltage: 1.71V to 3.6V (3.3V logic — directly compatible with Raspberry Pi GPIO)
•	Power Consumption: Ultra-low, less than 3.6 microamperes in forced mode

The BME280 connects to Raspberry Pi via the I2C bus using GPIO Pin 3 (SDA) and GPIO Pin 5 (SCL). The I2C address can be set to 0x76 (SDO to GND) or 0x77 (SDO to 3.3V). Python library used: adafruit-circuitpython-bme280.

4.2 PMS5003 — Particulate Matter Sensor
The PMS5003 by Plantower Technology is a laser-based optical particle counter. It uses a focused laser beam and photodetector to count and classify airborne particles by size in real time.

•	Parameters Detected: PM1.0, PM2.5, PM10 in micrograms per cubic meter (ug/m3)
•	Measurement Range: 0 to 500 ug/m3
•	Accuracy: +/- 10% for PM2.5 values between 100 to 500 ug/m3; +/- 10 ug/m3 for values 0 to 100
•	Response Time: Less than 10 seconds from power on to stable readings
•	Communication: UART serial at 9600 baud, 3.3V TTL logic level
•	Operating Voltage: 4.5V to 5.5V (requires 5V supply)

The PMS5003 transmits 32-byte data frames over UART every second. It is connected to Raspberry Pi GPIO23 (TX) and GPIO24 (RX). The sensor output voltage is 3.3V TTL, making it directly compatible without a level converter. Python library: pms5003.

4.3 CO2 Sensor (MH-Z19B)
The MH-Z19B is a Non-Dispersive Infrared (NDIR) CO2 sensor that measures carbon dioxide concentration by detecting the absorption of infrared light at CO2's specific wavelength (4.26 micrometers).

•	Detection Range: 0 to 5000 ppm (standard) | 0 to 2000 ppm (medical grade recommended)
•	Accuracy: +/- 50 ppm + 3% of reading value
•	Response Time: Less than 60 seconds for T90 response
•	Communication: UART at 9600 baud or PWM output
•	Operating Voltage: 4.5V to 5.5V
•	Warm-up Time: Minimum 3 minutes before valid readings

The MH-Z19B connects to Raspberry Pi via the primary UART interface (GPIO14 TX, GPIO15 RX). Note: The Raspberry Pi's serial console must be disabled in raspi-config to free up /dev/serial0 for sensor use. Python library: mh_z19.

4.4 Differential Pressure Sensor
A differential pressure sensor measures the pressure difference between two points in an HVAC system or across a filter. In OT rooms, this indicates whether the room maintains positive or negative pressure relative to adjacent spaces, critical for infection control.

•	Typical Measurement Range: 0 to 500 Pa or 0 to 1 inch Water Column (inWC)
•	Output Type: Analog voltage or I2C digital (model dependent)
•	Applications: HVAC filter status, room positive/negative pressure monitoring, airflow measurement
•	Recommended Models: SDP810 or SDP31 by Sensirion (I2C), MPXV7002 by NXP (Analog)

For analog output models, an MCP3008 Analog-to-Digital Converter (ADC) is required, connected to Raspberry Pi via SPI interface (GPIO10 MOSI, GPIO9 MISO, GPIO11 SCLK, GPIO8 CE0).

5. Circuit Diagram Description
 Provide me the complete pin-by-pin wiring description visulization not only the text. which software to use to create the actual visual circuit diagram.

 I ahd tried to generate the System Block Diagram below:

  [5V/3A Power Supply]
         |
  [Raspberry Pi 4 Model B]  ------  [7-inch Display via HDMI/DSI]
    |          |          |
 [I2C Bus]  [UART-1]  [UART-2]
    |          |          |
 [BME280] [CO2 MH-Z19] [PMS5003]
 [Diff.P]

6. System Working Principle
The OT Environment Monitoring System operates in a continuous, automated real-time loop. Below is the complete step-by-step working process from power-on to display output.

Step 1: System Initialization
1.	Raspberry Pi boots Raspberry Pi OS and auto-launches the monitoring application via /etc/rc.local or systemd service.
2.	I2C bus is enabled and scanned: sudo i2cdetect -y 1 confirms BME280 at address 0x76 or 0x77.
3.	UART ports are opened: /dev/serial0 for CO2 sensor, /dev/ttyS1 or USB adapter for PMS5003.
4.	CO2 sensor enters a 3-minute warm-up cycle; dashboard displays 'Warming Up...' during this period.
5.	Dashboard launches in full-screen mode on the connected display using Chromium browser or Tkinter window.

Step 2: Sensor Data Acquisition
1.	Every 2 seconds, Raspberry Pi polls all sensors concurrently using Python threading for non-blocking reads.
2.	BME280 returns: Temperature in degrees Celsius, Relative Humidity in percentage, Barometric Pressure in hPa.
3.	PMS5003 sends a 32-byte UART data frame containing PM1.0, PM2.5, and PM10 in micrograms per cubic meter.
4.	MH-Z19 CO2 sensor returns the carbon dioxide concentration in parts per million (ppm).
5.	Differential pressure sensor returns the pressure difference between two measurement points in Pascals.

Step 3: Data Processing and Validation
1.	Received data frames are parsed and validated for range errors and UART checksum verification.
2.	Invalid or out-of-range readings are discarded and flagged in the error log.
3.	A rolling average of the last 5 readings is computed for each parameter to reduce sensor noise.
4.	Each averaged value is compared to the predefined medical threshold table (WHO, ASHRAE, OSHA standards).
5.	A status level is assigned per parameter: Excellent (Green), Good (Yellow), or Warning (Red).

Step 4: Dashboard Display Update
1.	The dashboard interface updates every 2 seconds with the latest sensor readings via Flask API or WebSocket.
2.	Each sensor card shows: current numeric value, measurement unit, and color-coded status badge.
3.	Color coding: Green badge = Excellent, Yellow badge = Good, Red flashing badge = Warning.
4.	An audible alert (buzzer or speaker) and visual pop-up banner are triggered when any parameter enters Warning status.
5.	Historical trend graphs showing the last 60 minutes of data are displayed using Chart.js line charts.
-- Which we have already design previoulsy you can read the project file.

Step 5: Data Logging
 -- You can decide the data how to be stored so that our current working procedure should match and also can be future proof, like using cloud base database or any other database like mysql etc, whichever is faster and put less load to the communication use those.

7. Medical Criteria and Threshold Values
The system evaluates each sensor reading against the following medical and environmental standards: WHO 2021 Air Quality Guidelines, ASHRAE 55 and 62.1, and OSHA Indoor Air Quality standards.

•	EXCELLENT (Green): Values are within the ideal range for human health and comfort.
•	GOOD (Yellow): Values are within acceptable range but approaching their safe limits.
•	WARNING (Red): Values exceed safe limits — immediate ventilation or corrective action is required.

7.1 Particulate Matter Thresholds (WHO 2021)
Status	PM1.0 (ug/m3)	PM2.5 (ug/m3)	PM10 (ug/m3)
EXCELLENT	0 to 10	0 to 12	0 to 20
GOOD	10 to 25	12 to 35	20 to 50
WARNING	Above 25	Above 35	Above 50

7.2 Temperature and Humidity Thresholds (ASHRAE 55 / WHO)
Status	Temperature (deg C)	Humidity (%RH)	Pressure (hPa)
EXCELLENT	20 to 24	40 to 60%	1000 to 1020
GOOD	18 to 26	30 to 70%	990 to 1030
WARNING	Below 18 or Above 26	Below 30% or Above 70%	Below 990 or Above 1030

7.3 CO2 Concentration Thresholds (ASHRAE 62.1 / OSHA)
Status	CO2 Level (ppm)	Health Implication
EXCELLENT	400 to 800 ppm	Fresh air, ideal indoor air quality
GOOD	800 to 1200 ppm	Acceptable, slight stuffiness may occur
WARNING	Above 1200 ppm	Poor ventilation — open windows or increase airflow

7.4 Differential Pressure Thresholds
Status	Differential Pressure (Pa)	Indication
EXCELLENT	5 to 15 Pa	Normal room pressure differential
GOOD	2 to 20 Pa	Slight deviation, monitor closely
WARNING	Below 2 Pa or Above 20 Pa	Possible filter blockage or HVAC malfunction

8. Software Architecture
We have developed the Dashboard on the python and flutter, I think we should move further with this architecture only or for the basic communication you can use C++ so that we our hardware and software communication should not get stucked

9. Dashboard Design
- The Dashboard is being developed already as we previously work on the dashboard project, you can refer to the previous project file for the dashboard design.

10. Applications of the System
•	Occupational Therapy (OT) Rooms: Ensure clean, controlled air for sensitive patient recovery environments.
•	Hospital Wards and ICUs: Continuous air quality monitoring to support infection control protocols.
•	Pharmaceutical Manufacturing: Monitor particulate contamination levels in ISO-classified cleanrooms.
•	School Classrooms and Libraries: Detect CO2 buildup from poor ventilation and overcrowding.
•	Corporate Offices and Smart Buildings: HVAC control triggers and energy-efficient ventilation management.
•	Industrial Facilities and Warehouses: Worker safety monitoring for dust particles and gas exposure limits.
•	Research Laboratories: Maintain precise environmental conditions for experiments and biological samples.



**Note::: Generate the file accordingly and also for the safe side, you should generate a detailed described file whatever the requirement is mentioned above so that the developed dashboard should not get crashed.