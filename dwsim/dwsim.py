import clr
import System

clr.AddReference(r"C:\DWSIM\DWSIM.Automation.dll")
from DWSIM.Automation import Automation2

# cukup kasih path saja
path = System.String(r"C:\hello-rust\dwsim\heatexchangers.dwxmz")
sim = Automation2.LoadFlowsheet(path)

def run_simulation(temp_in):
    feed = sim.GetMaterialStream("1")  # ganti sesuai nama stream kamu
    feed.SetTemperature(temp_in + 273.15)
    feed.SetPressure(101325)

    sim.Run()  # jalankan flowsheet

    outlet = sim.GetMaterialStream("2")  # ganti sesuai nama stream outlet
    t_out = outlet.GetTemperature() - 273.15
    return t_out

if __name__ == "__main__":
    print("Inlet 30°C -> Outlet:", run_simulation(30), "°C")
    print("Inlet 50°C -> Outlet:", run_simulation(50), "°C")
