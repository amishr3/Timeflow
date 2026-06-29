"""
Seed demo data matching the HTML prototype.
Run once after `alembic upgrade head`:

    python seed.py
"""

import os
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

from app.core.auth import hash_password
from app.database import SessionLocal
from app.models.allocation import Allocation
from app.models.expense import Expense
from app.models.project import Project, ProjectAssignment
from app.models.timesheet import TimeEntry, Timesheet
from app.models.user import User

db = SessionLocal()

# ── Users ─────────────────────────────────────────────────────────────────────
manager = User(
    name="Alex Morgan",
    email="alex@timeflow.dev",
    hashed_password=hash_password("password123"),
    role="manager",
    team="Engineering",
    weekly_capacity_hours=40,
    billable_target_pct=70,
)
db.add(manager)
db.flush()

employees = [
    User(name="Priya Sharma",   email="priya@timeflow.dev",   hashed_password=hash_password("password123"), role="employee", team="Engineering",  weekly_capacity_hours=40, billable_target_pct=80, manager_id=manager.id),
    User(name="James Liu",      email="james@timeflow.dev",   hashed_password=hash_password("password123"), role="employee", team="Engineering",  weekly_capacity_hours=40, billable_target_pct=80, manager_id=manager.id),
    User(name="Sofia Reyes",    email="sofia@timeflow.dev",   hashed_password=hash_password("password123"), role="employee", team="Design",        weekly_capacity_hours=40, billable_target_pct=75, manager_id=manager.id),
    User(name="Tom Baker",      email="tom@timeflow.dev",     hashed_password=hash_password("password123"), role="employee", team="Engineering",  weekly_capacity_hours=40, billable_target_pct=80, manager_id=manager.id),
    User(name="Aisha Patel",    email="aisha@timeflow.dev",   hashed_password=hash_password("password123"), role="employee", team="QA",            weekly_capacity_hours=40, billable_target_pct=60, manager_id=manager.id),
]
for e in employees:
    db.add(e)
db.flush()

priya = employees[0]

# ── Projects ──────────────────────────────────────────────────────────────────
projects = [
    Project(name="Acme Corp Portal",    client="Acme Corp",     status="Active",    budget_hours=500,  hourly_rate=150, billable=True),
    Project(name="Nova Analytics",      client="Nova Inc",      status="Active",    budget_hours=300,  hourly_rate=130, billable=True),
    Project(name="Internal Platform",   client=None,            status="Active",    budget_hours=None, hourly_rate=None, billable=False),
    Project(name="Bright Future NGO",   client="Bright Future", status="Active",    budget_hours=200,  hourly_rate=95,  billable=True),
    Project(name="Quantum Retail App",  client="Quantum Ltd",   status="On Hold",   budget_hours=400,  hourly_rate=120, billable=True),
]
for p in projects:
    db.add(p)
db.flush()

acme, nova, internal, bright, quantum = projects

# Assign all employees to the first 3 projects
for emp in employees:
    for proj in [acme, nova, internal]:
        db.add(ProjectAssignment(user_id=emp.id, project_id=proj.id, role="contributor"))
db.flush()

# ── Timesheets & Entries (current week for Priya) ─────────────────────────────
today = date.today()
monday = today - timedelta(days=today.weekday())  # current Monday

ts = Timesheet(user_id=priya.id, week_start=monday, status="draft")
db.add(ts)
db.flush()

entries = [
    TimeEntry(user_id=priya.id, project_id=acme.id,     timesheet_id=ts.id, task="API development",     date=monday,              hours=4.0, billable=True),
    TimeEntry(user_id=priya.id, project_id=acme.id,     timesheet_id=ts.id, task="Code review",         date=monday,              hours=2.0, billable=True),
    TimeEntry(user_id=priya.id, project_id=nova.id,     timesheet_id=ts.id, task="Dashboard design",    date=monday+timedelta(1), hours=6.0, billable=True),
    TimeEntry(user_id=priya.id, project_id=internal.id, timesheet_id=ts.id, task="Sprint planning",     date=monday+timedelta(2), hours=1.5, billable=False),
    TimeEntry(user_id=priya.id, project_id=acme.id,     timesheet_id=ts.id, task="Bug fixes",           date=monday+timedelta(2), hours=5.5, billable=True),
    TimeEntry(user_id=priya.id, project_id=nova.id,     timesheet_id=ts.id, task="Analytics integration",date=monday+timedelta(3), hours=6.0, billable=True),
    TimeEntry(user_id=priya.id, project_id=acme.id,     timesheet_id=ts.id, task="Client call",         date=monday+timedelta(4), hours=1.0, billable=True),
    TimeEntry(user_id=priya.id, project_id=internal.id, timesheet_id=ts.id, task="Documentation",       date=monday+timedelta(4), hours=3.0, billable=False),
]
for entry in entries:
    db.add(entry)

# James Liu — submitted this week
ts_james = Timesheet(user_id=employees[1].id, week_start=monday, status="submitted")
db.add(ts_james)
db.flush()
for entry in [
    TimeEntry(user_id=employees[1].id, project_id=acme.id,     timesheet_id=ts_james.id, task="Feature development", date=monday,              hours=8.0, billable=True),
    TimeEntry(user_id=employees[1].id, project_id=acme.id,     timesheet_id=ts_james.id, task="Code review",         date=monday+timedelta(1), hours=6.0, billable=True),
    TimeEntry(user_id=employees[1].id, project_id=internal.id, timesheet_id=ts_james.id, task="Team standup",        date=monday+timedelta(1), hours=1.0, billable=False),
    TimeEntry(user_id=employees[1].id, project_id=acme.id,     timesheet_id=ts_james.id, task="Bug fixes",           date=monday+timedelta(2), hours=7.5, billable=True),
    TimeEntry(user_id=employees[1].id, project_id=internal.id, timesheet_id=ts_james.id, task="Documentation",       date=monday+timedelta(2), hours=1.5, billable=False),
    TimeEntry(user_id=employees[1].id, project_id=acme.id,     timesheet_id=ts_james.id, task="Sprint review",       date=monday+timedelta(3), hours=8.0, billable=True),
    TimeEntry(user_id=employees[1].id, project_id=acme.id,     timesheet_id=ts_james.id, task="Deployment",          date=monday+timedelta(4), hours=6.0, billable=True),
]:
    db.add(entry)

# Sofia Reyes — draft this week
ts_sofia = Timesheet(user_id=employees[2].id, week_start=monday, status="draft")
db.add(ts_sofia)
db.flush()
for entry in [
    TimeEntry(user_id=employees[2].id, project_id=nova.id,     timesheet_id=ts_sofia.id, task="UI mockups",          date=monday,              hours=6.0, billable=True),
    TimeEntry(user_id=employees[2].id, project_id=bright.id,   timesheet_id=ts_sofia.id, task="Brand guidelines",    date=monday,              hours=2.0, billable=True),
    TimeEntry(user_id=employees[2].id, project_id=nova.id,     timesheet_id=ts_sofia.id, task="Design review",       date=monday+timedelta(1), hours=5.0, billable=True),
    TimeEntry(user_id=employees[2].id, project_id=bright.id,   timesheet_id=ts_sofia.id, task="Illustration work",   date=monday+timedelta(1), hours=3.0, billable=True),
    TimeEntry(user_id=employees[2].id, project_id=internal.id, timesheet_id=ts_sofia.id, task="Design system",       date=monday+timedelta(2), hours=2.0, billable=False),
    TimeEntry(user_id=employees[2].id, project_id=nova.id,     timesheet_id=ts_sofia.id, task="Prototype iteration", date=monday+timedelta(2), hours=5.0, billable=True),
    TimeEntry(user_id=employees[2].id, project_id=bright.id,   timesheet_id=ts_sofia.id, task="Client presentation", date=monday+timedelta(3), hours=4.0, billable=True),
    TimeEntry(user_id=employees[2].id, project_id=nova.id,     timesheet_id=ts_sofia.id, task="Handoff prep",        date=monday+timedelta(4), hours=5.0, billable=True),
]:
    db.add(entry)

# Tom Baker — approved last week, draft this week
prev_monday = monday - timedelta(7)
ts_tom_prev = Timesheet(user_id=employees[3].id, week_start=prev_monday, status="approved")
db.add(ts_tom_prev)
db.flush()
for entry in [
    TimeEntry(user_id=employees[3].id, project_id=acme.id,    timesheet_id=ts_tom_prev.id, task="Backend dev",     date=prev_monday,              hours=8.0, billable=True),
    TimeEntry(user_id=employees[3].id, project_id=quantum.id, timesheet_id=ts_tom_prev.id, task="Architecture",    date=prev_monday+timedelta(1), hours=7.0, billable=True),
    TimeEntry(user_id=employees[3].id, project_id=acme.id,    timesheet_id=ts_tom_prev.id, task="API integration", date=prev_monday+timedelta(2), hours=8.0, billable=True),
    TimeEntry(user_id=employees[3].id, project_id=quantum.id, timesheet_id=ts_tom_prev.id, task="Testing",         date=prev_monday+timedelta(3), hours=6.0, billable=True),
    TimeEntry(user_id=employees[3].id, project_id=internal.id,timesheet_id=ts_tom_prev.id, task="Planning",        date=prev_monday+timedelta(4), hours=3.0, billable=False),
]:
    db.add(entry)

ts_tom = Timesheet(user_id=employees[3].id, week_start=monday, status="draft")
db.add(ts_tom)
db.flush()
for entry in [
    TimeEntry(user_id=employees[3].id, project_id=acme.id,    timesheet_id=ts_tom.id, task="Feature work",    date=monday,              hours=6.0, billable=True),
    TimeEntry(user_id=employees[3].id, project_id=quantum.id, timesheet_id=ts_tom.id, task="Bug triage",      date=monday+timedelta(1), hours=7.0, billable=True),
    TimeEntry(user_id=employees[3].id, project_id=acme.id,    timesheet_id=ts_tom.id, task="Code review",     date=monday+timedelta(2), hours=5.0, billable=True),
    TimeEntry(user_id=employees[3].id, project_id=internal.id,timesheet_id=ts_tom.id, task="Team meeting",    date=monday+timedelta(2), hours=1.0, billable=False),
    TimeEntry(user_id=employees[3].id, project_id=quantum.id, timesheet_id=ts_tom.id, task="Performance fix", date=monday+timedelta(3), hours=8.0, billable=True),
]:
    db.add(entry)

# Aisha Patel — submitted this week
ts_aisha = Timesheet(user_id=employees[4].id, week_start=monday, status="submitted")
db.add(ts_aisha)
db.flush()
for entry in [
    TimeEntry(user_id=employees[4].id, project_id=acme.id,    timesheet_id=ts_aisha.id, task="QA testing",      date=monday,              hours=6.0, billable=True),
    TimeEntry(user_id=employees[4].id, project_id=internal.id,timesheet_id=ts_aisha.id, task="Test planning",   date=monday,              hours=2.0, billable=False),
    TimeEntry(user_id=employees[4].id, project_id=acme.id,    timesheet_id=ts_aisha.id, task="Regression tests",date=monday+timedelta(1), hours=7.0, billable=True),
    TimeEntry(user_id=employees[4].id, project_id=acme.id,    timesheet_id=ts_aisha.id, task="Bug reporting",   date=monday+timedelta(2), hours=5.0, billable=True),
    TimeEntry(user_id=employees[4].id, project_id=internal.id,timesheet_id=ts_aisha.id, task="QA docs",         date=monday+timedelta(2), hours=2.0, billable=False),
    TimeEntry(user_id=employees[4].id, project_id=acme.id,    timesheet_id=ts_aisha.id, task="UAT support",     date=monday+timedelta(3), hours=6.0, billable=True),
    TimeEntry(user_id=employees[4].id, project_id=acme.id,    timesheet_id=ts_aisha.id, task="Sign-off review", date=monday+timedelta(4), hours=4.0, billable=True),
]:
    db.add(entry)

# ── Allocations (current week) ────────────────────────────────────────────────
alloc_data = [
    (priya,         [(acme, 24, True),  (nova, 12, True),  (internal, 4, False)]),
    (employees[1],  [(acme, 32, True),  (internal, 8, False)]),
    (employees[2],  [(nova, 20, True),  (bright, 16, True), (internal, 4, False)]),
    (employees[3],  [(acme, 16, True),  (quantum, 20, True), (internal, 4, False)]),
    (employees[4],  [(acme, 24, True),  (internal, 16, False)]),
]
for emp, allocations in alloc_data:
    for proj, hours, billable in allocations:
        db.add(Allocation(user_id=emp.id, project_id=proj.id, week_start=monday, planned_hours=hours, billable=billable))

# ── Expenses ──────────────────────────────────────────────────────────────────
expense_data = [
    Expense(user_id=priya.id,        project_id=acme.id,  date=monday-timedelta(3),  category="travel",    description="Flight to client site",    amount=340.00, billable=True,  status="submitted"),
    Expense(user_id=priya.id,        project_id=nova.id,  date=monday-timedelta(5),  category="software",  description="Figma annual subscription",  amount=144.00, billable=False, status="draft"),
    Expense(user_id=employees[1].id, project_id=acme.id,  date=monday-timedelta(2),  category="meals",     description="Client dinner",               amount=87.50,  billable=True,  status="submitted"),
    Expense(user_id=employees[2].id, project_id=None,     date=monday-timedelta(8),  category="equipment", description="Mechanical keyboard",         amount=229.99, billable=False, status="approved"),
    Expense(user_id=employees[3].id, project_id=acme.id,  date=monday-timedelta(1),  category="travel",    description="Train tickets",               amount=62.40,  billable=True,  status="submitted"),
]
for exp in expense_data:
    db.add(exp)

db.commit()
print("✓ Seed complete.")
print(f"\nLogin credentials (all use password: password123):")
print(f"  Manager : alex@timeflow.dev")
print(f"  Employee: priya@timeflow.dev  (prototype's main employee view)")
for e in employees[1:]:
    print(f"  Employee: {e.email}")
