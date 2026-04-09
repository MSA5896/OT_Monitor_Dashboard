I am getting the issue below when I run the main.py file

"""
:/Private/Development/ot_monitor/backend/main.py
d:\Private\Development\ot_monitor\backend\main.py:153: DeprecationWarning: 
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
        
  @app.on_event("startup")
d:\Private\Development\ot_monitor\backend\main.py:186: DeprecationWarning: 
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("shutdown")
INFO:     Started server process [25228]
INFO:     Waiting for application startup.
14:57:24  INFO      storage – Storage initialised: ./data/ot_monitor.db
14:57:24  INFO      data_sources.simulator_source – SimulatorSource started (scenario=normal)
14:57:24  INFO      ot_monitor – OT Monitor backend started  ✓  (ot_id=OT-01, source=simulator)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
"""


-- Look into all of the files for any issue as I go through many of the files.

Regarding the next step I want you do the installation of the required packages for the project. 1. Install Flutter SDK, 2. run flutter pub get, 3. test the dashboard against the simulator.


