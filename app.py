from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import threading

app = Flask(__name__)

# ============================================================
# LIFELINE - HACKMATRIX 5.0
# Real-Time Emergency Resource Allocator
# Simulated prototype for Round 1
# ============================================================

# Simulated hospital data
hospitals = [
    {
        "id": 1,
        "name": "City Care Hospital",
        "location": "Central City",
        "icu": 3,
        "ventilator": 2,
        "trauma": True,
        "blood": True,
        "cath_lab": True,
        "travel_time": 8,
        "data_age": 2,
    },
    {
        "id": 2,
        "name": "Metro General Hospital",
        "location": "North Zone",
        "icu": 2,
        "ventilator": 1,
        "trauma": True,
        "blood": True,
        "cath_lab": False,
        "travel_time": 12,
        "data_age": 5,
    },
    {
        "id": 3,
        "name": "LifeCare Medical Centre",
        "location": "East Zone",
        "icu": 1,
        "ventilator": 1,
        "trauma": True,
        "blood": False,
        "cath_lab": True,
        "travel_time": 10,
        "data_age": 3,
    },
    {
        "id": 4,
        "name": "Sunrise Hospital",
        "location": "South Zone",
        "icu": 4,
        "ventilator": 3,
        "trauma": False,
        "blood": True,
        "cath_lab": True,
        "travel_time": 18,
        "data_age": 35,
    },
    {
        "id": 5,
        "name": "Unity Trauma Centre",
        "location": "West Zone",
        "icu": 1,
        "ventilator": 2,
        "trauma": True,
        "blood": True,
        "cath_lab": False,
        "travel_time": 14,
        "data_age": 4,
    },
]

reservations = []
request_counter = 1001
lock = threading.Lock()


def is_stale(hospital):
    """Hospital data older than 15 minutes is treated as stale."""
    return hospital["data_age"] > 15


def resource_match(hospital, required):
    """Check whether a hospital has every required resource."""
    if required.get("icu") and hospital["icu"] <= 0:
        return False

    if required.get("ventilator") and hospital["ventilator"] <= 0:
        return False

    if required.get("trauma") and not hospital["trauma"]:
        return False

    if required.get("blood") and not hospital["blood"]:
        return False

    if required.get("cath_lab") and not hospital["cath_lab"]:
        return False

    return True


def calculate_score(hospital):
    """
    Ranking:
    - Resource match: 50%
    - Travel time: 30%
    - Freshness: 20%
    """

    resource_score = 100

    travel_score = max(0, 100 - hospital["travel_time"] * 3)

    freshness_score = max(0, 100 - hospital["data_age"] * 3)

    score = (
        0.50 * resource_score
        + 0.30 * travel_score
        + 0.20 * freshness_score
    )

    if is_stale(hospital):
        score -= 15

    return round(score, 2)


def get_hospital(hospital_id):
    for hospital in hospitals:
        if hospital["id"] == hospital_id:
            return hospital
    return None


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/api/hospitals")
def get_hospitals():
    result = []

    for hospital in hospitals:
        item = hospital.copy()
        item["stale"] = is_stale(hospital)
        item["score"] = calculate_score(hospital)
        result.append(item)

    return jsonify(result)


@app.route("/api/match", methods=["POST"])
def match_hospitals():
    global request_counter

    data = request.get_json()

    required = {
        "icu": data.get("icu", False),
        "ventilator": data.get("ventilator", False),
        "trauma": data.get("trauma", False),
        "blood": data.get("blood", False),
        "cath_lab": data.get("cath_lab", False),
    }

    with lock:
        request_id = request_counter
        request_counter += 1

    matches = []

    for hospital in hospitals:

        if resource_match(hospital, required):
            item = hospital.copy()
            item["score"] = calculate_score(hospital)
            item["stale"] = is_stale(hospital)
            matches.append(item)

    matches.sort(key=lambda x: x["score"], reverse=True)

    return jsonify({
        "request_id": request_id,
        "matches": matches
    })


@app.route("/api/reserve", methods=["POST"])
def reserve_resource():
    data = request.get_json()

    hospital_id = data.get("hospital_id")
    required = data.get("required", {})

    hospital = get_hospital(hospital_id)

    if not hospital:
        return jsonify({
            "success": False,
            "message": "Hospital not found."
        }), 404

    with lock:

        # Atomic-style validation for the prototype.
        # Re-check availability immediately before reservation.

        if required.get("icu") and hospital["icu"] <= 0:
            return jsonify({
                "success": False,
                "message": "ICU resource is no longer available."
            })

        if required.get("ventilator") and hospital["ventilator"] <= 0:
            return jsonify({
                "success": False,
                "message": "Ventilator is no longer available."
            })

        if required.get("trauma") and not hospital["trauma"]:
            return jsonify({
                "success": False,
                "message": "Trauma facility unavailable."
            })

        if required.get("blood") and not hospital["blood"]:
            return jsonify({
                "success": False,
                "message": "Blood resource unavailable."
            })

        if required.get("cath_lab") and not hospital["cath_lab"]:
            return jsonify({
                "success": False,
                "message": "Cath lab unavailable."
            })

        # Reserve resources
        if required.get("icu"):
            hospital["icu"] -= 1

        if required.get("ventilator"):
            hospital["ventilator"] -= 1

        reservation = {
            "hospital": hospital["name"],
            "created_at": datetime.now().isoformat(),
            "expires_at": (
                datetime.now() + timedelta(minutes=10)
            ).isoformat(),
            "status": "RESERVED"
        }

        reservations.append(reservation)

    return jsonify({
        "success": True,
        "message": f"Resources reserved at {hospital['name']}.",
        "reservation": reservation
    })


@app.route("/api/demo/double-booking", methods=["POST"])
def double_booking_demo():

    # Find a hospital with exactly one ICU bed.
    hospital = next(
        (h for h in hospitals if h["icu"] == 1),
        None
    )

    if not hospital:
        return jsonify({
            "success": False,
            "message": "No single-bed ICU scenario available."
        })

    with lock:

        # First request gets the last ICU bed.
        if hospital["icu"] > 0:
            hospital["icu"] -= 1
            first = "Request A → ICU RESERVED"
        else:
            first = "Request A → REJECTED"

        # Second request checks again.
        if hospital["icu"] > 0:
            hospital["icu"] -= 1
            second = "Request B → ICU RESERVED"
        else:
            second = "Request B → REJECTED / RE-RANK"

    return jsonify({
        "hospital": hospital["name"],
        "result": [
            first,
            second
        ],
        "message": "Only one request can claim the final ICU resource."
    })


@app.route("/api/handover", methods=["POST"])
def handover():

    return jsonify({
        "status": "HANDED OVER",
        "steps": [
            "Request accepted",
            "Resources reserved",
            "Ambulance dispatched",
            "Ambulance en route",
            "Hospital preparing",
            "Patient arrived",
            "Patient handed over"
        ]
    })


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Lifeline - Emergency Resource Allocator</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f4f7fb;
            color: #172033;
        }

        header {
            background: linear-gradient(
                135deg,
                #0b3954,
                #087e8b
            );
            color: white;
            padding: 28px;
        }

        header h1 {
            margin: 0;
            font-size: 32px;
        }

        header p {
            margin: 8px 0 0;
            opacity: 0.9;
        }

        .container {
            max-width: 1200px;
            margin: 25px auto;
            padding: 0 20px;
        }

        .grid {
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 20px;
        }

        .card {
            background: white;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.07);
        }

        h2 {
            margin-top: 0;
        }

        label {
            display: block;
            margin: 13px 0 6px;
            font-weight: bold;
        }

        input[type="checkbox"] {
            margin-right: 8px;
        }

        button {
            border: none;
            border-radius: 8px;
            padding: 11px 16px;
            cursor: pointer;
            font-weight: bold;
            margin-top: 12px;
        }

        .primary {
            background: #087e8b;
            color: white;
            width: 100%;
        }

        .demo {
            background: #7b2cbf;
            color: white;
            width: 100%;
        }

        .hospital {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
        }

        .hospital h3 {
            margin: 0 0 5px;
        }

        .score {
            font-size: 25px;
            font-weight: bold;
            color: #087e8b;
        }

        .badges {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }

        .badge {
            background: #edf2f7;
            padding: 5px 8px;
            border-radius: 20px;
            font-size: 12px;
        }

        .stale {
            background: #fff3cd;
            color: #856404;
            padding: 8px;
            border-radius: 8px;
            margin-top: 10px;
        }

        .success {
            background: #d1fae5;
            color: #065f46;
            padding: 12px;
            border-radius: 8px;
            margin-top: 12px;
        }

        .danger {
            background: #fee2e2;
            color: #991b1b;
            padding: 12px;
            border-radius: 8px;
            margin-top: 12px;
        }

        .steps {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .step {
            background: #e8f3f5;
            padding: 9px 12px;
            border-radius: 20px;
            font-size: 13px;
        }

        @media(max-width: 800px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }

    </style>
</head>

<body>

<header>
    <div class="container">
        <h1>🚑 LIFELINE</h1>
        <p>
            Live Hospital Matching & Emergency Handover
        </p>
    </div>
</header>

<div class="container">

    <div class="card">

        <h2>Emergency Workflow</h2>

        <div class="steps">
            <span class="step">1. Request</span>
            <span class="step">2. Filter</span>
            <span class="step">3. Rank</span>
            <span class="step">4. Accept</span>
            <span class="step">5. Reserve</span>
            <span class="step">6. Handover</span>
        </div>

    </div>

    <div class="grid">

        <div>

            <div class="card">

                <h2>Emergency Request</h2>

                <p>
                    Select the resources required for the patient.
                </p>

                <label>
                    <input type="checkbox" id="icu">
                    ICU Bed
                </label>

                <label>
                    <input type="checkbox" id="ventilator">
                    Ventilator
                </label>

                <label>
                    <input type="checkbox" id="trauma">
                    Trauma Centre
                </label>

                <label>
                    <input type="checkbox" id="blood">
                    Blood
                </label>

                <label>
                    <input type="checkbox" id="cath_lab">
                    Cath Lab
                </label>

                <button
                    class="primary"
                    onclick="findHospitals()">
                    Find Matching Hospitals
                </button>

            </div>

            <div class="card">

                <h2>Prototype Tests</h2>

                <button
                    class="demo"
                    onclick="doubleBooking()">
                    Test Double Booking
                </button>

                <button
                    class="demo"
                    onclick="handover()">
                    Simulate Handover
                </button>

                <div id="testResult"></div>

            </div>

        </div>

        <div>

            <div class="card">

                <h2>Ranked Hospitals</h2>

                <div id="results">
                    <p>
                        Submit an emergency request
                        to see available hospitals.
                    </p>
                </div>

            </div>

        </div>

    </div>

</div>

<script>

async function findHospitals() {

    const required = {
        icu: document.getElementById("icu").checked,
        ventilator:
            document.getElementById("ventilator").checked,
        trauma:
            document.getElementById("trauma").checked,
        blood:
            document.getElementById("blood").checked,
        cath_lab:
            document.getElementById("cath_lab").checked
    };

    const response = await fetch("/api/match", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(required)
    });

    const data = await response.json();

    const results =
        document.getElementById("results");

    if (data.matches.length === 0) {

        results.innerHTML =
            `<div class="danger">
                No hospital currently satisfies
                all required resources.
            </div>`;

        return;
    }

    results.innerHTML = "";

    data.matches.forEach(hospital => {

        const card =
            document.createElement("div");

        card.className = "hospital";

        let staleMessage = "";

        if (hospital.stale) {

            staleMessage =
                `<div class="stale">
                    ⚠ Data is stale.
                    Hospital confirmation required
                    before dispatch.
                </div>`;
        }

        card.innerHTML = `
            <h3>${hospital.name}</h3>

            <p>${hospital.location}</p>

            <div class="score">
                ${hospital.score}
            </div>

            <small>Matching Score</small>

            <div class="badges">

                <span class="badge">
                    ICU: ${hospital.icu}
                </span>

                <span class="badge">
                    Ventilator:
                    ${hospital.ventilator}
                </span>

                <span class="badge">
                    Travel:
                    ${hospital.travel_time} min
                </span>

                <span class="badge">
                    Data:
                    ${hospital.data_age} min old
                </span>

            </div>

            ${staleMessage}

            <button
                class="primary"
                onclick='reserve(
                    ${hospital.id},
                    ${JSON.stringify(required)}
                )'>
                Accept & Reserve
            </button>
        `;

        results.appendChild(card);
    });
}


async function reserve(hospitalId, required) {

    const response = await fetch("/api/reserve", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            hospital_id: hospitalId,
            required: required
        })

    });

    const data = await response.json();

    const results =
        document.getElementById("results");

    if (data.success) {

        results.insertAdjacentHTML(
            "afterbegin",
            `<div class="success">
                ✅ ${data.message}
                <br>
                Reservation valid for
                approximately 10 minutes.
            </div>`
        );

    } else {

        results.insertAdjacentHTML(
            "afterbegin",
            `<div class="danger">
                ❌ ${data.message}
            </div>`
        );
    }
}


async function doubleBooking() {

    const response =
        await fetch(
            "/api/demo/double-booking",
            {
                method: "POST"
            }
        );

    const data =
        await response.json();

    document.getElementById(
        "testResult"
    ).innerHTML = `
        <div class="success">
            <strong>Double Booking Test</strong>
            <br><br>
            ${data.result.join("<br>")}
            <br><br>
            ${data.message}
        </div>
    `;
}


async function handover() {

    const response =
        await fetch(
            "/api/handover",
            {
                method: "POST"
            }
        );

    const data =
        await response.json();

    document.getElementById(
        "testResult"
    ).innerHTML = `
        <div class="success">
            <strong>
                Handover Workflow
            </strong>

            <br><br>

            ${data.steps.join(
                "<br>↓<br>"
            )}
        </div>
    `;
}

</script>

</body>
</html>
"""


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
