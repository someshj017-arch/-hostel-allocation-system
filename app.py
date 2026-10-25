from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from datetime import date
import os

app = Flask(__name__, template_folder='my_templates')
app.secret_key = 'hostel_secret_key_2026'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': os.getenv('DB_PASSWORD', 'Hostel@2026'),
    'database': 'hostel_allocation'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/availability')
def availability():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT h.hostel_name, r.room_id, r.room_number,
               r.capacity, r.current_occupancy,
               (r.capacity - r.current_occupancy) AS available_beds
        FROM Room r JOIN Hostel h ON r.hostel_id = h.hostel_id
        ORDER BY h.hostel_name, r.room_number
    """)
    rooms = cursor.fetchall()
    db.close()
    return render_template('availability.html', rooms=rooms)

@app.route('/students')
def students():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Student ORDER BY student_id")
    students = cursor.fetchall()
    db.close()
    return render_template('students.html', students=students)

@app.route('/allocate', methods=['GET', 'POST'])
def allocate():
    if request.method == 'POST':
        student_id = request.form['student_id']
        hostel_id = request.form['hostel_id']
        db = get_db()
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT room_id FROM Room
                WHERE hostel_id = %s AND current_occupancy < capacity
                LIMIT 1 FOR UPDATE
            """, (hostel_id,))
            room = cursor.fetchone()
            if not room:
                flash('No available rooms in this hostel!', 'error')
                return redirect(url_for('allocate'))
            cursor.execute("""
                INSERT INTO Allocation (student_id, room_id, allocation_date, status)
                VALUES (%s, %s, %s, 'Active')
            """, (student_id, room['room_id'], date.today()))
            cursor.execute("""
                UPDATE Room SET current_occupancy = current_occupancy + 1
                WHERE room_id = %s
            """, (room['room_id'],))
            db.commit()
            flash(f'Room allocated successfully! Room ID: {room["room_id"]}', 'success')
        except mysql.connector.Error as e:
            db.rollback()
            flash(f'Error: {e}', 'error')
        finally:
            db.close()
        return redirect(url_for('allocations'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Student ORDER BY name")
    students_list = cursor.fetchall()
    cursor.execute("SELECT * FROM Hostel ORDER BY hostel_name")
    hostels = cursor.fetchall()
    db.close()
    return render_template('allocate.html', students=students_list, hostels=hostels)

@app.route('/allocations')
def allocations():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.allocation_id, s.name AS student_name, s.email,
               h.hostel_name, r.room_number,
               a.allocation_date, a.vacate_date, a.status
        FROM Allocation a
        JOIN Student s ON a.student_id = s.student_id
        JOIN Room r ON a.room_id = r.room_id
        JOIN Hostel h ON r.hostel_id = h.hostel_id
        ORDER BY a.allocation_id DESC
    """)
    allocations_list = cursor.fetchall()
    db.close()
    return render_template('allocations.html', allocations=allocations_list)

@app.route('/vacate/<int:allocation_id>', methods=['POST'])
def vacate(allocation_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT room_id FROM Allocation
            WHERE allocation_id = %s AND status = 'Active'
        """, (allocation_id,))
        alloc = cursor.fetchone()
        if not alloc:
            flash('No active allocation found', 'error')
            return redirect(url_for('allocations'))
        cursor.execute("""
            UPDATE Allocation SET status = 'Vacated', vacate_date = %s
            WHERE allocation_id = %s
        """, (date.today(), allocation_id))
        cursor.execute("""
            UPDATE Room SET current_occupancy = current_occupancy - 1
            WHERE room_id = %s
        """, (alloc['room_id'],))
        db.commit()
        flash('Room vacated successfully!', 'success')
    except mysql.connector.Error as e:
        db.rollback()
        flash(f'Error: {e}', 'error')
    finally:
        db.close()
    return redirect(url_for('allocations'))

if __name__ == '__main__':
    app.run(debug=True)