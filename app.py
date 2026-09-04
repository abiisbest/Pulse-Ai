from flask import Flask, render_template_string, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore
import os

app = Flask(__name__)

# Initialize Firebase Admin & Firestore
# (Make sure to place your serviceAccountKey.json in the project folder, 
# or set the GOOGLE_APPLICATION_CREDENTIALS environment variable)
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        # Fallback for cloud deployment using environment variables or default auth
        firebase_admin.initialize_app()

db = firestore.client()

# --- FIRESTORE DATABASE VERIFICATION TEST ---
try:
    # Attempt a quick write/read test to prove database connection on startup
    test_ref = db.collection("system_logs").document("connection_test")
    test_ref.set({"status": "Connected successfully", "timestamp": firestore.SERVER_TIMESTAMP})
    print("SUCCESS: Connected to Google Cloud Firestore Database!")
except Exception as e:
    print(f"DATABASE CONNECTION WARNING: {e}")

@app.route("/")
def index():
    # Fetch live data from Firestore collections
    try:
        patients_ref = db.collection("patients").stream()
        patients = [doc.to_dict() for doc in patients_ref]
        if not patients:
            patients = [{"id": "MRN-8842", "name": "Robert Fox", "age": 62, "gender": "Male", "complaint": "Acute Angina", "doctor": "Dr. Sarah Jenkins", "ward": "Cardio Bed-02", "waitTime": "0m", "apptTime": "10:30 AM", "status": "In Consultation"}]
    except Exception:
        patients = []

    try:
        beds_ref = db.collection("beds").stream()
        beds = [doc.to_dict() for doc in beds_ref]
        if not beds:
            beds = [{"id": "ICU-1", "ward": "ICU", "status": "occupied", "patient": "R. Fox"}]
    except Exception:
        beds = []

    staffMembers = {
        "ed": [{"name": "Dr. Michael Chang", "role": "Attending Physician", "load": "85%"}],
        "icu": [{"name": "Dr. Elena Rostova", "role": "Intensivist", "load": "78%"}],
        "standby": [{"name": "Dr. Lucas Hood", "role": "General Surgeon", "status": "Standby"}]
    }

    return render_template_string(HTML_TEMPLATE, patients=patients, beds=beds, staffMembers=staffMembers)


# --- DATABASE DIAGNOSTIC ROUTE (Proof of Connection) ---
@app.route("/db-status")
def db_status():
    try:
        # Fetch collection counts/documents to prove live database interaction
        docs = list(db.collection("system_logs").stream())
        return jsonify({
            "database": "Google Cloud Firestore",
            "status": "Online & Active",
            "connection_proof": "Successfully queried Firestore collection 'system_logs'",
            "record_count": len(docs)
        }), 200
    except Exception as e:
        return jsonify({
            "database": "Google Cloud Firestore",
            "status": "Error",
            "details": str(e)
        }), 500


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PulseAI - Smart Healthcare & Multi-Role Flow Management</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; }
    .custom-scroll::-webkit-scrollbar { width: 6px; height: 6px; }
    .custom-scroll::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
    .custom-scroll::-webkit-scrollbar-thumb:hover { background: #475569; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 flex h-screen overflow-hidden">
  <aside class="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0">
    <div>
      <div class="h-16 flex items-center px-6 gap-3 border-b border-slate-800">
        <div class="h-9 w-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <i class="fa-solid fa-heart-pulse text-white text-lg"></i>
        </div>
        <div>
          <h1 class="font-bold text-base leading-none text-white tracking-wide">PulseAI</h1>
          <span class="text-[10px] text-cyan-400 font-semibold tracking-wider uppercase" id="sidebar-role-badge">Admin Portal</span>
        </div>
      </div>
      <nav class="p-4 space-y-1.5 text-sm" id="dynamic-nav"></nav>
    </div>
    <div class="p-4 border-t border-slate-800 space-y-3">
      <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex items-center justify-between">
        <div>
          <p class="text-[10px] uppercase font-bold text-slate-400">Database Status</p>
          <a href="/db-status" target="_blank" class="text-xs text-emerald-400 font-semibold hover:underline flex items-center gap-1 mt-0.5">
            <i class="fa-solid fa-database text-[10px]"></i> Firestore Live ✓
          </a>
        </div>
      </div>
      <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
        <label class="block text-[10px] uppercase font-bold text-slate-400 mb-1.5">Switch Active Role</label>
        <select id="role-selector" onchange="switchRole(this.value)" class="w-full bg-slate-800 border border-slate-700 text-xs text-cyan-400 rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:border-cyan-500">
          <option value="admin">Admin Portal</option>
          <option value="doctor">Doctor Portal</option>
          <option value="patient">Patient Portal</option>
        </select>
      </div>
      <div class="flex items-center gap-3 px-1 pt-1" id="user-profile-card"></div>
    </div>
  </aside>

  <div class="flex-1 flex flex-col overflow-hidden">
    <header class="h-16 bg-slate-900/60 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-8 z-10 shrink-0">
      <div class="flex items-center gap-4">
        <div class="relative w-72">
          <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 text-xs"></i>
          <input type="text" id="global-search" placeholder="Search records, appointments, beds..." class="w-full pl-9 pr-4 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors">
        </div>
        <div class="h-4 w-[1px] bg-slate-800"></div>
        <span class="inline-flex items-center gap-2 text-xs text-slate-400">
          <i class="fa-regular fa-clock text-slate-500"></i>
          <span id="current-time">10:45 AM</span> | Facility: <strong class="text-slate-200 font-medium">Metro Health Hub</strong>
        </span>
      </div>
      <div class="flex items-center gap-3" id="header-actions"></div>
    </header>

    <main class="flex-1 overflow-y-auto p-8 custom-scroll bg-slate-950">
      <div id="view-admin" class="space-y-6">
        <div id="admin-subview-flow" class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl">
              <div class="flex items-center justify-between">
                <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Beds In Use</span>
                <div class="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <i class="fa-solid fa-bed text-xs"></i>
                </div>
              </div>
              <div class="mt-4 flex items-baseline gap-2">
                <span class="text-3xl font-bold text-white tracking-tight" id="admin-bed-stat">221/250</span>
                <span class="text-xs font-semibold text-rose-400">88.4%</span>
              </div>
              <p class="mt-1 text-xs text-slate-400">29 Available across 4 wards</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl">
              <div class="flex items-center justify-between">
                <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg ED Wait Time</span>
                <div class="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <i class="fa-solid fa-hourglass-half text-xs"></i>
                </div>
              </div>
              <div class="mt-4 flex items-baseline gap-2">
                <span class="text-3xl font-bold text-white tracking-tight">16.2 <span class="text-sm font-normal text-slate-400">min</span></span>
                <span class="text-xs font-semibold text-emerald-400">-14%</span>
              </div>
              <p class="mt-1 text-xs text-slate-400">Target: &lt; 25.0 min</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl">
              <div class="flex items-center justify-between">
                <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Surgeries</span>
                <div class="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <i class="fa-solid fa-microscope text-xs"></i>
                </div>
              </div>
              <div class="mt-4 flex items-baseline gap-2">
                <span class="text-3xl font-bold text-white tracking-tight">4 <span class="text-sm font-normal text-slate-400">ORs</span></span>
                <span class="text-xs font-semibold text-purple-400">1 Standby</span>
              </div>
              <p class="mt-1 text-xs text-slate-400">OR Turnaround Latency: 11m</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl">
              <div class="flex items-center justify-between">
                <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Staff On Duty</span>
                <div class="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                  <i class="fa-solid fa-user-nurse text-xs"></i>
                </div>
              </div>
              <div class="mt-4 flex items-baseline gap-2">
                <span class="text-3xl font-bold text-white tracking-tight">48</span>
                <span class="text-xs font-semibold text-emerald-400">Balanced</span>
              </div>
              <p class="mt-1 text-xs text-slate-400">12 Doctors, 36 RNs active</p>
            </div>
          </div>
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
              <h2 class="text-sm font-bold text-white tracking-wide mb-1">Facility Patient Volume vs Capacity Flow</h2>
              <p class="text-xs text-slate-400 mb-4">Hourly throughput analytics across all emergency and inpatient admissions</p>
              <div class="h-64"><canvas id="adminFlowChart"></canvas></div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
              <div>
                <h2 class="text-sm font-bold text-white tracking-wide mb-3">Resource Ward Allocation</h2>
                <div class="space-y-3 text-xs">
                  <div>
                    <div class="flex justify-between text-slate-300 font-medium mb-1">
                      <span>Emergency Department (ED)</span>
                      <span class="text-rose-400 font-semibold">92%</span>
                    </div>
                    <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div class="bg-rose-500 h-full rounded-full" style="width: 92%"></div>
                    </div>
                  </div>
                  <div>
                    <div class="flex justify-between text-slate-300 font-medium mb-1">
                      <span>Intensive Care Unit (ICU)</span>
                      <span class="text-amber-400 font-semibold">80%</span>
                    </div>
                    <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div class="bg-amber-400 h-full rounded-full" style="width: 80%"></div>
                    </div>
                  </div>
                  <div>
                    <div class="flex justify-between text-slate-300 font-medium mb-1">
                      <span>General Surgery</span>
                      <span class="text-emerald-400 font-semibold">60%</span>
                    </div>
                    <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div class="bg-emerald-400 h-full rounded-full" style="width: 60%"></div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mt-4 p-3 bg-slate-950 border border-slate-800 rounded-xl">
                <p class="text-xs font-semibold text-slate-200">Shift Alert</p>
                <p class="text-[11px] text-slate-400 mt-0.5">ICU bed assignment turnover is approaching target thresholds.</p>
              </div>
            </div>
          </div>
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-sm font-bold text-white tracking-wide">Live Hospital Patient Flow Register (Firestore Connected)</h2>
              <span class="text-xs text-cyan-400 font-mono" id="admin-patient-count">4 Active Records</span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs text-slate-300">
                <thead class="bg-slate-950 text-slate-400 font-semibold uppercase tracking-wider text-[10px] border-b border-slate-800">
                  <tr>
                    <th class="py-3 px-4">Patient / MRN</th>
                    <th class="py-3 px-4">Age / Sex</th>
                    <th class="py-3 px-4">Condition</th>
                    <th class="py-3 px-4">Assigned Doctor</th>
                    <th class="py-3 px-4">Status / Ward</th>
                    <th class="py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/60" id="admin-patient-table-body"></tbody>
              </table>
            </div>
          </div>
        </div>

        <div id="admin-subview-matrix" class="space-y-6 hidden">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 class="text-base font-bold text-white tracking-wide">Real-time Ward & Bed Matrix</h2>
              <p class="text-xs text-slate-400">Interactive ward mapping with quick status toggles</p>
            </div>
            <div class="flex items-center gap-2">
              <select id="admin-matrix-filter" onchange="renderAdminBedMatrix()" class="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500">
                <option value="ALL">All Departments</option>
                <option value="ICU">ICU</option>
                <option value="ED">Emergency (ED)</option>
                <option value="CARDIO">Cardiology</option>
                <option value="SURGERY">Surgical Recovery</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3.5" id="admin-bed-matrix-grid"></div>
        </div>

        <div id="admin-subview-roster" class="space-y-6 hidden">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-base font-bold text-white tracking-wide">Facility Staff Rostering & Coverage</h2>
              <p class="text-xs text-slate-400">Active personnel workload allocation and standby coverage</p>
            </div>
            <button onclick="rebalanceStaff()" class="bg-cyan-500/10 border border-cyan-500/30 hover:bg-cyan-500/20 text-cyan-400 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-2">
              <i class="fa-solid fa-arrows-rotate"></i> Auto-Balance Shifts
            </button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <h3 class="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">Emergency Department</h3>
              <div class="space-y-3" id="admin-staff-ed"></div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <h3 class="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">Intensive Care Unit (ICU)</h3>
              <div class="space-y-3" id="admin-staff-icu"></div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <h3 class="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">Standby & On-Call Pool</h3>
              <div class="space-y-3" id="admin-staff-standby"></div>
            </div>
          </div>
        </div>

        <div id="admin-subview-settings" class="space-y-6 hidden">
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl max-w-2xl space-y-5">
            <div>
              <h2 class="text-base font-bold text-white tracking-wide">System Configuration & Thresholds</h2>
              <p class="text-xs text-slate-400">Configure operational alerts and facility resource capacities</p>
            </div>
            <div class="space-y-4 text-xs">
              <div>
                <label class="block text-slate-300 font-medium mb-1">Max ED Wait Time Threshold (Minutes)</label>
                <input type="number" value="25" class="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-cyan-500">
              </div>
              <div>
                <label class="block text-slate-300 font-medium mb-1">Critical ICU Bed Warning Capacity (%)</label>
                <input type="number" value="85" class="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-cyan-500">
              </div>
              <div class="flex items-center justify-between p-3 bg-slate-950 rounded-xl border border-slate-800">
                <div>
                  <p class="font-semibold text-slate-200">Automatic Triage Protocol Routing</p>
                  <p class="text-[11px] text-slate-400">Direct critical ESI 1 & 2 cases to acute trauma units</p>
                </div>
                <input type="checkbox" checked class="w-4 h-4 accent-cyan-500">
              </div>
              <button onclick="alert('System settings updated successfully.')" class="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-xs transition-colors">
                Save System Parameters
              </button>
            </div>
          </div>
        </div>
      </div>

      <div id="view-doctor" class="space-y-6 hidden">
        <div id="doc-subview-queue" class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-5">
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl">
              <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Patients in Waiting Area</span>
              <div class="mt-3 flex items-baseline gap-2">
                <span class="text-3xl font-bold text-amber-400" id="doc-waiting-count">3</span>
                <span class="text-xs text-slate-400">Next: 10:45 AM</span>
              </div>
              <p class="mt-1 text-xs text-slate-400">Avg wait: 12 mins</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl">
              <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Today's Appointments</span>
              <div class="mt-3 flex items-baseline gap-2">
                <span class="text-3xl font-bold text-white">8</span>
                <span class="text-xs text-emerald-400 font-semibold">5 Completed</span>
              </div>
              <p class="mt-1 text-xs text-slate-400">Shift ends at 17:00</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl">
              <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Inpatients</span>
              <div class="mt-3 flex items-baseline gap-2">
                <span class="text-3xl font-bold text-rose-400">2</span>
                <span class="text-xs text-slate-400">ICU Bed 01 & 04</span>
              </div>
              <p class="mt-1 text-xs text-slate-400">Rounds required by 13:00</p>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl">
              <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Pending Lab Reviews</span>
              <div class="mt-3 flex items-baseline gap-2">
                <span class="text-3xl font-bold text-cyan-400">4</span>
                <span class="text-xs text-amber-400">1 Urgent STAT</span>
              </div>
              <p class="mt-1 text-xs text-slate-400">Troponin, CBC, CT scan</p>
            </div>
          </div>
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
              <div class="flex items-center justify-between mb-4">
                <div>
                  <h2 class="text-sm font-bold text-white tracking-wide">Doctor's Schedule & Waiting Queue</h2>
                  <p class="text-xs text-slate-400">Direct consultation order and live triage status</p>
                </div>
                <button onclick="callNextPatient()" class="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-3 py-1.5 rounded-lg text-xs transition-all flex items-center gap-1.5">
                  <i class="fa-solid fa-bullhorn"></i> Call Next Patient
                </button>
              </div>
              <div class="space-y-3" id="doc-patient-queue"></div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
              <div>
                <h2 class="text-sm font-bold text-white tracking-wide mb-3">Active Consultation Notes</h2>
                <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 text-xs">
                  <div>
                    <span class="text-slate-400 text-[10px] uppercase font-bold">Current Patient</span>
                    <p class="text-sm font-bold text-white" id="doc-active-consult-name">Robert Fox (62y, M)</p>
                    <p class="text-slate-400 text-[11px]">MRN-8842 | Chief Complaint: Acute Angina</p>
                  </div>
                  <div>
                    <label class="block text-slate-400 mb-1 font-semibold">Clinical Prescription / Order</label>
                    <textarea id="doc-note-text" rows="4" placeholder="Enter clinical assessment, medications, or ward transfer directives..." class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"></textarea>
                  </div>
                </div>
              </div>
              <button onclick="saveDoctorAssessment()" class="w-full mt-4 bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 rounded-xl text-xs transition-colors">
                Save Clinical Assessment
              </button>
            </div>
          </div>
        </div>

        <div id="doc-subview-appts" class="space-y-6 hidden">
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 class="text-sm font-bold text-white tracking-wide mb-3">Today's Appointment Schedule</h2>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs text-slate-300">
                <thead class="bg-slate-950 text-slate-400 font-semibold uppercase tracking-wider text-[10px] border-b border-slate-800">
                  <tr>
                    <th class="py-3 px-4">Time</th>
                    <th class="py-3 px-4">Patient</th>
                    <th class="py-3 px-4">Type</th>
                    <th class="py-3 px-4">Status</th>
                    <th class="py-3 px-4">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/60" id="doc-appts-table-body"></tbody>
              </table>
            </div>
          </div>
        </div>

        <div id="doc-subview-diagnostics" class="space-y-6 hidden">
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 class="text-sm font-bold text-white tracking-wide mb-4">Patient Diagnostic Workorders</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs" id="doc-diagnostics-list"></div>
          </div>
        </div>

        <div id="doc-subview-prescriptions" class="space-y-6 hidden">
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-sm font-bold text-white tracking-wide">Pharmacy & Prescription Log</h2>
              <button onclick="alert('Prescription order form initialized.')" class="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-3 py-1.5 rounded-lg text-xs transition-colors">
                + New Rx Order
              </button>
            </div>
            <div class="space-y-3" id="doc-prescriptions-list"></div>
          </div>
        </div>
      </div>

      <div id="view-patient" class="space-y-6 hidden">
        <div id="patient-subview-status" class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-slate-900/90 border border-slate-800 p-6 rounded-2xl shadow-xl flex flex-col justify-between">
              <div>
                <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Your Live Queue Status</span>
                <div class="mt-4 text-center py-4 bg-slate-950 rounded-xl border border-slate-800">
                  <p class="text-xs text-slate-400">Position in Line</p>
                  <p class="text-4xl font-extrabold text-cyan-400 my-1" id="patient-queue-pos">#2</p>
                  <p class="text-xs font-medium text-emerald-400">Estimated wait: ~10 mins</p>
                </div>
              </div>
              <div class="mt-4 pt-3 border-t border-slate-800 text-xs text-slate-400">
                Assigned Specialist: <strong class="text-white">Dr. Sarah Jenkins</strong>
              </div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-6 rounded-2xl shadow-xl flex flex-col justify-between">
              <div>
                <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Upcoming Scheduled Slot</span>
                <div class="mt-4 bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
                  <div class="flex justify-between"><span class="text-slate-400">Appointment Time:</span><span class="font-bold text-white">10:45 AM</span></div>
                  <div class="flex justify-between"><span class="text-slate-400">Clinic:</span><span class="font-bold text-cyan-400">Cardiology & Vascular</span></div>
                  <div class="flex justify-between"><span class="text-slate-400">Room:</span><span class="font-bold text-slate-200">Suite 302</span></div>
                </div>
              </div>
              <button onclick="switchTab('patient', 'book')" class="mt-4 w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-2 rounded-lg text-xs transition-colors">
                Reschedule / Book New
              </button>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-6 rounded-2xl shadow-xl flex flex-col justify-between">
              <div>
                <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Care Team Contact</span>
                <div class="mt-4 space-y-2.5 text-xs">
                  <div class="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
                    <div><p class="font-semibold text-white">Nurse Station West</p><p class="text-[10px] text-slate-400">Ext: 4044</p></div>
                    <span class="text-cyan-400 text-xs font-bold"><i class="fa-solid fa-phone"></i></span>
                  </div>
                  <div class="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
                    <div><p class="font-semibold text-white">Pharmacy Desk</p><p class="text-[10px] text-slate-400">Ext: 2018</p></div>
                    <span class="text-cyan-400 text-xs font-bold"><i class="fa-solid fa-phone"></i></span>
                  </div>
                </div>
              </div>
              <div class="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400">
                Insurance: <strong class="text-slate-200">Blue Shield PPO (#8912-A)</strong>
              </div>
            </div>
          </div>
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 class="text-sm font-bold text-white tracking-wide mb-3">Your Hospital Care Timeline</h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
              <div class="p-4 bg-slate-950 border border-cyan-500/40 rounded-xl relative">
                <span class="text-cyan-400 font-bold text-[10px] uppercase">Step 1</span>
                <p class="font-semibold text-white mt-1">Intake & Triage</p>
                <p class="text-[11px] text-emerald-400 mt-1">✓ Completed at 10:15 AM</p>
              </div>
              <div class="p-4 bg-slate-950 border border-amber-500/40 rounded-xl relative">
                <span class="text-amber-400 font-bold text-[10px] uppercase">Step 2</span>
                <p class="font-semibold text-white mt-1">Doctor Consultation</p>
                <p class="text-[11px] text-amber-400 mt-1">● In Progress (Waiting #2)</p>
              </div>
              <div class="p-4 bg-slate-950 border border-slate-800 rounded-xl relative opacity-60">
                <span class="text-slate-400 font-bold text-[10px] uppercase">Step 3</span>
                <p class="font-semibold text-white mt-1">Diagnostics / Labs</p>
                <p class="text-[11px] text-slate-400 mt-1">Scheduled next</p>
              </div>
              <div class="p-4 bg-slate-950 border border-slate-800 rounded-xl relative opacity-60">
                <span class="text-slate-400 font-bold text-[10px] uppercase">Step 4</span>
                <p class="font-semibold text-white mt-1">Discharge & Rx</p>
                <p class="text-[11px] text-slate-400 mt-1">Pending consult</p>
              </div>
            </div>
          </div>
        </div>

        <div id="patient-subview-book" class="space-y-6 hidden">
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl max-w-lg">
            <h2 class="text-sm font-bold text-white tracking-wide mb-1">Book a Specialist Consultation</h2>
            <p class="text-xs text-slate-400 mb-4">Request a slot with hospital physicians</p>
            <form onsubmit="handlePatientBooking(event)" class="space-y-3 text-xs">
              <div>
                <label class="block text-slate-400 mb-1">Select Department</label>
                <select id="book-dept" class="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500">
                  <option>Cardiology Specialist</option>
                  <option>General Medicine</option>
                  <option>Orthopedic Clinic</option>
                  <option>Pediatrics</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-400 mb-1">Reason / Symptoms</label>
                <input type="text" id="book-reason" required placeholder="e.g. Follow-up consultation, recurring migraine" class="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500">
              </div>
              <button type="submit" class="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold py-2 rounded-lg transition-all">
                Request Appointment Slot
              </button>
            </form>
          </div>
        </div>

        <div id="patient-subview-records" class="space-y-6 hidden">
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 class="text-sm font-bold text-white tracking-wide mb-3">Electronic Medical Records</h2>
            <div class="space-y-3 text-xs">
              <div class="p-3.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between">
                <div><p class="font-semibold text-white">Full Blood Count (FBC) & Electrolytes</p><p class="text-[11px] text-slate-400">Processed by Central Lab &bull; Result: Normal parameters</p></div>
                <button onclick="alert('Downloading Diagnostic PDF...')" class="text-xs bg-slate-800 hover:bg-slate-700 text-cyan-400 font-semibold px-3 py-1.5 rounded-lg transition-colors"><i class="fa-solid fa-download mr-1"></i> PDF</button>
              </div>
              <div class="p-3.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between">
                <div><p class="font-semibold text-white">Digital 12-Lead Electrocardiogram (ECG)</p><p class="text-[11px] text-slate-400">Processed by Cardiology Unit &bull; Result: Sinus Rhythm</p></div>
                <button onclick="alert('Downloading Diagnostic PDF...')" class="text-xs bg-slate-800 hover:bg-slate-700 text-cyan-400 font-semibold px-3 py-1.5 rounded-lg transition-colors"><i class="fa-solid fa-download mr-1"></i> PDF</button>
              </div>
            </div>
          </div>
        </div>

        <div id="patient-subview-billing" class="space-y-6 hidden">
          <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl max-w-xl">
            <h2 class="text-sm font-bold text-white tracking-wide mb-3">Billing & Insurance Statement</h2>
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
              <div class="flex justify-between"><span class="text-slate-400">Total Admission Charges:</span><span class="text-white font-mono font-bold">$1,240.00</span></div>
              <div class="flex justify-between"><span class="text-slate-400">Covered by Insurance (Blue Shield 90%):</span><span class="text-emerald-400 font-mono font-bold">-$1,116.00</span></div>
              <div class="h-[1px] bg-slate-800 my-2"></div>
              <div class="flex justify-between text-sm"><span class="font-semibold text-white">Patient Co-pay Balance:</span><span class="text-cyan-400 font-mono font-bold">$124.00</span></div>
            </div>
            <button onclick="alert('Redirecting to secure payment gateway...')" class="mt-4 w-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold py-2 rounded-lg text-xs transition-colors">
              Pay Balance Online
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>

  <div id="patient-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
      <div class="flex justify-between items-center border-b border-slate-800 pb-3">
        <h3 class="font-bold text-sm text-white">Admit / Register New Patient</h3>
        <button onclick="closePatientModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleAdminAdmit(event)" class="space-y-3 text-xs">
        <div>
          <label class="block text-slate-300 font-medium mb-1">Full Name</label>
          <input type="text" id="m-name" required placeholder="Patient Name" class="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-cyan-500">
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-slate-300 font-medium mb-1">Age</label>
            <input type="number" id="m-age" required placeholder="Age" class="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-cyan-500">
          </div>
          <div>
            <label class="block text-slate-300 font-medium mb-1">Department</label>
            <select id="m-dept" class="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-cyan-500">
              <option value="Emergency ED">Emergency ED</option>
              <option value="Cardiology">Cardiology</option>
              <option value="ICU">ICU</option>
              <option value="General Ward">General Ward</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-slate-300 font-medium mb-1">Chief Complaint</label>
          <input type="text" id="m-reason" required placeholder="Diagnosis / Symptom" class="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white focus:outline-none focus:border-cyan-500">
        </div>
        <div class="pt-2 flex justify-end gap-2">
          <button type="button" onclick="closePatientModal()" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg">Cancel</button>
          <button type="submit" class="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-lg">Register & Assign</button>
        </div>
      </form>
    </div>
  </div>

  <script>
    let currentRole = 'admin';
    let currentTab = { admin: 'flow', doctor: 'queue', patient: 'status' };

    let patients = {{ patients | tojson }};
    let beds = {{ beds | tojson }};
    let staffMembers = {{ staffMembers | tojson }};

    const rolesConfig = {
      admin: {
        badge: 'Admin Portal',
        nav: [
          { id: 'flow', icon: 'fa-chart-pie', label: 'Hospital Flow' },
          { id: 'matrix', icon: 'fa-bed-pulse', label: 'Ward Matrix' },
          { id: 'roster', icon: 'fa-user-nurse', label: 'Staff Roster' },
          { id: 'settings', icon: 'fa-sliders', label: 'System Settings' }
        ],
        profile: { name: 'Chief Administrator', sub: 'Operations Command', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=60' }
      },
      doctor: {
        badge: 'Doctor Portal',
        nav: [
          { id: 'queue', icon: 'fa-user-clock', label: 'Waiting Queue' },
          { id: 'appts', icon: 'fa-calendar-check', label: 'My Appointments' },
          { id: 'diagnostics', icon: 'fa-file-waveform', label: 'Patient Diagnostics' },
          { id: 'prescriptions', icon: 'fa-prescription-bottle-medical', label: 'Prescriptions' }
        ],
        profile: { name: 'Dr. Sarah Jenkins', sub: 'Cardiology Lead', avatar: 'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=100&auto=format&fit=crop&q=60' }
      },
      patient: {
        badge: 'Patient Portal',
        nav: [
          { id: 'status', icon: 'fa-house-user', label: 'My Queue Status' },
          { id: 'book', icon: 'fa-calendar-plus', label: 'Book Appointment' },
          { id: 'records', icon: 'fa-notes-medical', label: 'Health Records' },
          { id: 'billing', icon: 'fa-receipt', label: 'Billing & Insurance' }
        ],
        profile: { name: 'Emily Watson', sub: 'Patient (MRN-9102)', avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&auto=format&fit=crop&q=60' }
      }
    };

    function switchRole(role) {
      currentRole = role;
      document.getElementById('role-selector').value = role;
      document.getElementById('sidebar-role-badge').textContent = rolesConfig[role].badge;
      ['admin', 'doctor', 'patient'].forEach(r => { document.getElementById(`view-${r}`).classList.add('hidden'); });
      document.getElementById(`view-${role}`).classList.remove('hidden');
      renderSidebarNav();
      renderUserProfile();
      renderHeaderActions();
      switchTab(role, currentTab[role]);
    }

    function switchTab(role, tabId) {
      currentTab[role] = tabId;
      rolesConfig[role].nav.forEach(item => {
        const subview = document.getElementById(`${role === 'doctor' ? 'doc' : role}-subview-${item.id}`);
        if (subview) {
          if (item.id === tabId) { subview.classList.remove('hidden'); } else { subview.classList.add('hidden'); }
        }
      });
      renderSidebarNav();
      if (role === 'admin') {
        if (tabId === 'flow') { renderAdminTables(); initAdminFlowChart(); }
        else if (tabId === 'matrix') { renderAdminBedMatrix(); }
        else if (tabId === 'roster') { renderAdminStaff(); }
      } else if (role === 'doctor') {
        if (tabId === 'queue') { renderDoctorView(); }
        else if (tabId === 'appts') { renderDoctorAppointments(); }
        else if (tabId === 'diagnostics') { renderDoctorDiagnostics(); }
        else if (tabId === 'prescriptions') { renderDoctorPrescriptions(); }
      }
    }

    function renderSidebarNav() {
      const navContainer = document.getElementById('dynamic-nav');
      const items = rolesConfig[currentRole].nav;
      const activeId = currentTab[currentRole];
      navContainer.innerHTML = items.map(item => `
        <button onclick="switchTab('${currentRole}', '${item.id}')" class="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl font-medium transition-all ${
          item.id === activeId ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
        }">
          <i class="fa-solid ${item.icon} w-5"></i>
          <span>${item.label}</span>
        </button>
      `).join('');
    }

    function renderUserProfile() {
      const prof = rolesConfig[currentRole].profile;
      document.getElementById('user-profile-card').innerHTML = `
        <img src="${prof.avatar}" alt="${prof.name}" class="w-9 h-9 rounded-full object-cover ring-2 ring-cyan-500/40">
        <div class="truncate">
          <p class="text-xs font-semibold text-slate-200 truncate">${prof.name}</p>
          <p class="text-[10px] text-slate-400 truncate">${prof.sub}</p>
        </div>
      `;
    }

    function renderHeaderActions() {
      const container = document.getElementById('header-actions');
      if (currentRole === 'admin') {
        container.innerHTML = `
          <button onclick="openPatientModal()" class="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-lg shadow-cyan-500/20 transition-all">
            <i class="fa-solid fa-plus text-xs"></i>
            <span>Admit Patient</span>
          </button>
        `;
      } else if (currentRole === 'doctor') {
        container.innerHTML = `
          <span class="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-lg font-medium">
            <i class="fa-solid fa-circle text-[8px] mr-1"></i> Available for Consults
          </span>
        `;
      } else {
        container.innerHTML = `
          <button onclick="alert('Help desk notified. A nurse will assist shortly.')" class="flex items-center gap-1.5 bg-rose-500 hover:bg-rose-400 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors">
            <i class="fa-solid fa-bell"></i> Call Assistance
          </button>
        `;
      }
    }

    function renderAdminTables() {
      const tbody = document.getElementById('admin-patient-table-body');
      tbody.innerHTML = patients.map((p, idx) => `
        <tr class="hover:bg-slate-800/40 transition-colors">
          <td class="py-3 px-4">
            <p class="font-semibold text-white">${p.name}</p>
            <p class="text-[10px] text-slate-400">${p.id}</p>
          </td>
          <td class="py-3 px-4">${p.age}y / ${p.gender}</td>
          <td class="py-3 px-4 text-slate-200 font-medium">${p.complaint}</td>
          <td class="py-3 px-4 text-slate-300">${p.doctor}</td>
          <td class="py-3 px-4">
            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">${p.ward}</span>
          </td>
          <td class="py-3 px-4">
            <button onclick="dischargePatient(${idx})" class="text-rose-400 hover:underline text-[11px] font-semibold">Discharge</button>
          </td>
        </tr>
      `).join('');
      document.getElementById('admin-patient-count').textContent = `${patients.length} Active Records`;
    }

    function dischargePatient(index) {
      patients.splice(index, 1);
      renderAdminTables();
    }

    function renderAdminBedMatrix() {
      const filter = document.getElementById('admin-matrix-filter').value;
      const grid = document.getElementById('admin-bed-matrix-grid');
      const filtered = filter === 'ALL' ? beds : beds.filter(b => b.ward === filter);
      grid.innerHTML = filtered.map(b => {
        let statusBg = 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400';
        let icon = 'fa-bed';
        if (b.status === 'occupied') { statusBg = 'bg-rose-500/10 border-rose-500/30 text-rose-400'; }
        else if (b.status === 'cleaning') { statusBg = 'bg-amber-500/10 border-amber-500/30 text-amber-400'; icon = 'fa-soap'; }
        return `
          <div class="bg-slate-900 border ${statusBg} p-3.5 rounded-xl flex flex-col justify-between h-28 relative cursor-pointer hover:border-slate-500 transition-colors" onclick="toggleBedStatus('${b.id}')">
            <div class="flex items-center justify-between">
              <span class="font-bold text-xs text-white">${b.id}</span>
              <i class="fa-solid ${icon} text-xs"></i>
            </div>
            <div>
              <p class="text-[11px] font-semibold text-slate-200 truncate">${b.patient}</p>
              <p class="text-[9px] text-slate-400 uppercase tracking-wider">${b.status}</p>
            </div>
          </div>
        `;
      }).join('');
    }

    function toggleBedStatus(bedId) {
      const b = beds.find(x => x.id === bedId);
      if (!b) return;
      if (b.status === 'occupied') { b.status = 'cleaning'; b.patient = '--'; }
      else if (b.status === 'cleaning') { b.status = 'available'; }
      else { b.status = 'occupied'; b.patient = 'Admitted Patient'; }
      renderAdminBedMatrix();
    }

    function renderAdminStaff() {
      document.getElementById('admin-staff-ed').innerHTML = staffMembers.ed.map(s => `
        <div class="flex items-center justify-between p-2.5 bg-slate-800/60 rounded-xl border border-slate-700/60 text-xs">
          <div><p class="font-semibold text-slate-100">${s.name}</p><p class="text-[10px] text-slate-400">${s.role}</p></div>
          <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">${s.load} Load</span>
        </div>
      `).join('');
      document.getElementById('admin-staff-icu').innerHTML = staffMembers.icu.map(s => `
        <div class="flex items-center justify-between p-2.5 bg-slate-800/60 rounded-xl border border-slate-700/60 text-xs">
          <div><p class="font-semibold text-slate-100">${s.name}</p><p class="text-[10px] text-slate-400">${s.role}</p></div>
          <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">${s.load} Load</span>
        </div>
      `).join('');
      document.getElementById('admin-staff-standby').innerHTML = staffMembers.standby.map(s => `
        <div class="flex items-center justify-between p-2.5 bg-slate-800/60 rounded-xl border border-slate-700/60 text-xs">
          <div><p class="font-semibold text-slate-100">${s.name}</p><p class="text-[10px] text-slate-400">${s.role}</p></div>
          <span class="text-[11px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${s.status}</span>
        </div>
      `).join('');
    }

    function rebalanceStaff() {
      staffMembers.ed[1].load = '74%';
      staffMembers.icu[1].load = '80%';
      renderAdminStaff();
      alert('Shift workloads normalized across ED and ICU units.');
    }

    function renderDoctorView() {
      const queueList = document.getElementById('doc-patient-queue');
      const docPatients = patients.filter(p => p.doctor === 'Dr. Sarah Jenkins' || p.status === 'Waiting');
      document.getElementById('doc-waiting-count').textContent = docPatients.filter(p => p.status === 'Waiting').length;
      queueList.innerHTML = docPatients.map((p, idx) => `
        <div class="flex items-center justify-between p-3.5 bg-slate-950/80 rounded-xl border border-slate-800">
          <div class="flex items-center gap-3">
            <span class="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center text-cyan-400 font-bold text-xs">${idx + 1}</span>
            <div>
              <p class="font-bold text-white text-xs">${p.name} <span class="text-[10px] text-slate-400 font-normal">(${p.id})</span></p>
              <p class="text-[11px] text-slate-400">${p.complaint} &bull; <strong class="text-slate-300">${p.ward}</strong></p>
            </div>
          </div>
          <div class="text-right flex items-center gap-4">
            <div>
              <p class="text-xs font-mono font-bold text-cyan-400">${p.apptTime}</p>
              <p class="text-[10px] text-slate-400">Wait: ${p.waitTime}</p>
            </div>
            <button onclick="startConsultation('${p.name}', '${p.id}', '${p.complaint}')" class="px-3 py-1.5 bg-slate-800 hover:bg-cyan-500 hover:text-slate-950 text-slate-200 text-xs font-semibold rounded-lg transition-colors">
              ${p.status === 'In Consultation' ? 'Active' : 'Consult'}
            </button>
          </div>
        </div>
      `).join('');
    }

    function renderDoctorAppointments() {
      const tbody = document.getElementById('doc-appts-table-body');
      tbody.innerHTML = patients.map(p => `
        <tr class="hover:bg-slate-800/40">
          <td class="py-3 px-4 font-mono font-bold text-cyan-400">${p.apptTime}</td>
          <td class="py-3 px-4 text-white font-medium">${p.name}</td>
          <td class="py-3 px-4 text-slate-300">${p.complaint}</td>
          <td class="py-3 px-4">
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${p.status === 'In Consultation' ? 'bg-cyan-500/20 text-cyan-300' : 'bg-amber-500/20 text-amber-300'}">${p.status}</span>
          </td>
          <td class="py-3 px-4">
            <button onclick="startConsultation('${p.name}', '${p.id}', '${p.complaint}')" class="text-cyan-400 hover:underline">Open File</button>
          </td>
        </tr>
      `).join('');
    }

    function renderDoctorDiagnostics() {
      const list = document.getElementById('doc-diagnostics-list');
      list.innerHTML = `
        <div class="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
          <div class="flex justify-between"><span class="font-bold text-white">Robert Fox (MRN-8842)</span><span class="text-rose-400 font-semibold uppercase text-[10px]">STAT Urgent</span></div>
          <p class="text-slate-400">Order: Troponin-I + 12-Lead ECG</p>
          <div class="flex justify-between items-center pt-2">
            <span class="text-[11px] text-emerald-400">Lab Ready</span>
            <button onclick="alert('Viewing Robert Fox diagnostics')" class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-400 rounded">Review</button>
          </div>
        </div>
        <div class="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
          <div class="flex justify-between"><span class="font-bold text-white">Emily Watson (MRN-9102)</span><span class="text-cyan-400 font-semibold uppercase text-[10px]">Routine</span></div>
          <p class="text-slate-400">Order: Right Lower Extremity X-Ray</p>
          <div class="flex justify-between items-center pt-2">
            <span class="text-[11px] text-amber-400">In Imaging</span>
            <button onclick="alert('Imaging in progress...')" class="px-2.5 py-1 bg-slate-800 text-slate-500 rounded cursor-not-allowed">Review</button>
          </div>
        </div>
      `;
    }

    function renderDoctorPrescriptions() {
      const list = document.getElementById('doc-prescriptions-list');
      list.innerHTML = `
        <div class="p-3.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
          <div><p class="font-bold text-white">Aspirin 81mg & Atorvastatin 40mg</p><p class="text-[11px] text-slate-400">Prescribed to Robert Fox &bull; Once daily oral</p></div>
          <span class="text-emerald-400 font-semibold text-[11px]">Dispensed</span>
        </div>
        <div class="p-3.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
          <div><p class="font-bold text-white">Morphine Sulfate 2mg IV STAT</p><p class="text-[11px] text-slate-400">Prescribed to Emily Watson &bull; Acute trauma pain</p></div>
          <span class="text-amber-400 font-semibold text-[11px]">Administering</span>
        </div>
      `;
    }

    function startConsultation(name, id, complaint) {
      switchTab('doctor', 'queue');
      document.getElementById('doc-active-consult-name').textContent = `${name} (${id})`;
      alert(`Active file set to: ${name}`);
    }

    function saveDoctorAssessment() {
      const text = document.getElementById('doc-note-text').value;
      if (!text) { alert('Please enter consultation notes before saving.'); return; }
      alert('Clinical assessment and pharmacy orders dispatched!');
      document.getElementById('doc-note-text').value = '';
    }

    function callNextPatient() {
      const next = patients.find(p => p.status === 'Waiting');
      if (next) {
        next.status = 'In Consultation';
        startConsultation(next.name, next.id, next.complaint);
        renderDoctorView();
      } else {
        alert('No more patients waiting in queue!');
      }
    }

    function handlePatientBooking(e) {
      e.preventDefault();
      const reason = document.getElementById('book-reason').value;
      const dept = document.getElementById('book-dept').value;
      const newId = 'MRN-' + Math.floor(1000 + Math.random() * 9000);
      patients.push({
        id: newId,
        name: 'Emily Watson',
        age: 29,
        gender: 'Female',
        complaint: reason,
        doctor: 'Dr. Sarah Jenkins',
        ward: `${dept} Ward`,
        waitTime: '0m',
        apptTime: '11:45 AM',
        status: 'Waiting'
      });
      alert(`Appointment requested for ${dept}! Added to schedule.`);
      document.getElementById('book-reason').value = '';
      switchTab('patient', 'status');
    }

    function openPatientModal() { document.getElementById('patient-modal').classList.remove('hidden'); }
    function closePatientModal() { document.getElementById('patient-modal').classList.add('hidden'); }

    function handleAdminAdmit(e) {
      e.preventDefault();
      const name = document.getElementById('m-name').value;
      const age = document.getElementById('m-age').value;
      const dept = document.getElementById('m-dept').value;
      const reason = document.getElementById('m-reason').value;
      const newId = 'MRN-' + Math.floor(1000 + Math.random() * 9000);
      patients.unshift({
        id: newId,
        name: name,
        age: age,
        gender: 'Adult',
        complaint: reason,
        doctor: 'Dr. Sarah Jenkins',
        ward: `${dept} Bed`,
        waitTime: '0m',
        apptTime: '12:00 PM',
        status: 'Waiting'
      });
      renderAdminTables();
      closePatientModal();
      alert(`Patient ${name} registered successfully.`);
    }

    let chartInstance = null;
    function initAdminFlowChart() {
      const ctx = document.getElementById('adminFlowChart').getContext('2d');
      if (chartInstance) chartInstance.destroy();
      chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00'],
          datasets: [{
            label: 'Admissions Flow',
            data: [14, 28, 45, 52, 48, 38, 26, 18],
            borderColor: '#06b6d4',
            backgroundColor: 'rgba(6, 182, 212, 0.15)',
            tension: 0.4,
            fill: true,
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: '#1e293b' }, ticks: { color: '#64748b', font: { size: 10 } } },
            y: { grid: { color: '#1e293b' }, ticks: { color: '#64748b', font: { size: 10 } } }
          }
        }
      });
    }

    function updateClock() {
      const now = new Date();
      document.getElementById('current-time').textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    window.onload = () => {
      switchRole('admin');
      setInterval(updateClock, 1000);
      updateClock();
    };
  </script>
</body>
</html>"""

if __name__ == "__main__":
    app.run(debug=True, port=5000)
