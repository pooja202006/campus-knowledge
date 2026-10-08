import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

os.makedirs('sample_docs', exist_ok=True)

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontSize=18,
    leading=22,
    textColor=colors.HexColor('#1e3a8a'),
    spaceAfter=12
)
heading_style = ParagraphStyle(
    'SectionHeading',
    parent=styles['Heading2'],
    fontSize=14,
    leading=18,
    textColor=colors.HexColor('#0f766e'),
    spaceBefore=10,
    spaceAfter=6
)
body_style = ParagraphStyle(
    'DocBody',
    parent=styles['Normal'],
    fontSize=10,
    leading=14,
    spaceAfter=6
)

# 1. Academic_Calendar_2026.pdf
doc1 = SimpleDocTemplate("sample_docs/Academic_Calendar_2026.pdf", pagesize=letter)
story1 = [
    Paragraph("NEXUS INSTITUTE OF TECHNOLOGY — ACADEMIC CALENDAR 2026", title_style),
    Paragraph("Department of Academic Affairs | Circular Ref: NIT/AC/2026/01", body_style),
    Spacer(1, 10),
    Paragraph("Section 1: Commencement of Classes", heading_style),
    Paragraph("All Odd Semester classes for B.Tech II, III, and IV year students will officially commence on July 15, 2026. Freshmen (I Year B.Tech) orientation program will begin on August 1, 2026.", body_style),
    Paragraph("Section 2: Mid-Semester Examination Schedule", heading_style),
    Paragraph("Mid-Semester Examinations (Internal Assessment I) for all engineering departments are scheduled from September 20, 2026 to September 27, 2026. Hall tickets will be issued by respective HODs on September 15, 2026.", body_style),
    PageBreak(),
    Paragraph("Section 3: End Semester Examinations", heading_style),
    Paragraph("The End Semester Theory Examinations will commence on November 15, 2026 and conclude on December 5, 2026. Practical laboratory examinations will take place between November 5, 2026 and November 12, 2026.", body_style),
    Paragraph("Section 4: Winter Vacation & Semester Registration", heading_style),
    Paragraph("Winter vacation for students will be from December 6, 2026 to January 4, 2027. Registration for Even Semester (2027) will open on January 5, 2027.", body_style)
]
doc1.build(story1)

# 2. Examination_Rules_and_Fee_Notice.pdf
doc2 = SimpleDocTemplate("sample_docs/Examination_Rules_and_Fee_Notice.pdf", pagesize=letter)
story2 = [
    Paragraph("OFFICE OF THE CONTROLLER OF EXAMINATIONS", title_style),
    Paragraph("Notice: Semester Examination Fee & Attendance Rules 2026", body_style),
    Spacer(1, 10),
    Paragraph("Section 1: Examination Fee Structure", heading_style),
    Paragraph("The examination fee per regular theory paper is Rs. 250, and per practical lab course is Rs. 300. The last date to pay the semester exam fee without fine is October 10, 2026.", body_style),
    Paragraph("Section 2: Late Fee Penalty", heading_style),
    Paragraph("Fees paid between October 11, 2026 and October 18, 2026 will attract a late fine of Rs. 500. No fee payment will be accepted after October 18 under any circumstances.", body_style),
    PageBreak(),
    Paragraph("Section 3: Mandatory Attendance Requirement", heading_style),
    Paragraph("Students must maintain a minimum of 75% attendance in each course to be eligible to sit for end-semester examinations. Students with attendance between 65% and 74% due to medical reasons must submit a valid medical certificate along with a condonation fee of Rs. 1,000.", body_style),
    Paragraph("Section 4: Revaluation and Arrear Exams", heading_style),
    Paragraph("Applications for revaluation of answer scripts must be submitted within 7 days of result publication. The revaluation fee is Rs. 750 per paper. Supplementary/Arrear exam fee is Rs. 400 per subject.", body_style)
]
doc2.build(story2)

# 3. BTech_CSE_Syllabus_Electives.pdf
doc3 = SimpleDocTemplate("sample_docs/BTech_CSE_Syllabus_Electives.pdf", pagesize=letter)
story3 = [
    Paragraph("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING", title_style),
    Paragraph("Curriculum & Professional Electives Guide 2026-2027", body_style),
    Spacer(1, 10),
    Paragraph("Section 1: Semester V Core Courses", heading_style),
    Paragraph("Semester V core courses include: CS501 Database Management Systems (4 Credits), CS502 Operating Systems (4 Credits), CS503 Theory of Computation (3 Credits), and CS504 Artificial Intelligence (3 Credits).", body_style),
    Paragraph("Section 2: Professional Elective Track I (AI & Data Science)", heading_style),
    Paragraph("Elective options under Track I: CS-E01 Machine Learning (3 Credits), CS-E02 Natural Language Processing (3 Credits), CS-E03 Computer Vision (3 Credits), and CS-E04 Deep Learning Architecture (3 Credits). Prerequisites for NLP: CS504 AI.", body_style),
    PageBreak(),
    Paragraph("Section 3: Professional Elective Track II (Cybersecurity & Cloud)", heading_style),
    Paragraph("Elective options under Track II: CS-E11 Cryptography & Network Security (3 Credits), CS-E12 Cloud Computing Architecture (3 Credits), CS-E13 Blockchain Technology (3 Credits), and CS-E14 Penetration Testing (3 Credits).", body_style),
    Paragraph("Section 4: Mandatory Mini-Project Guidelines", heading_style),
    Paragraph("All 3rd-year CSE students must complete a mandatory Mini-Project (CS508) carrying 2 credits. Teams of max 3 students must submit project proposals by August 25, 2026 to the Project Coordinator Prof. Ramesh.", body_style)
]
doc3.build(story3)

# 4. Hostel_and_Bus_Transport_Guidelines.pdf
doc4 = SimpleDocTemplate("sample_docs/Hostel_and_Bus_Transport_Guidelines.pdf", pagesize=letter)
story4 = [
    Paragraph("CAMPUS FACILITIES & STUDENT SERVICES DIRECTORET", title_style),
    Paragraph("Hostel Rules & Campus Bus Transport Timetable 2026", body_style),
    Spacer(1, 10),
    Paragraph("Section 1: Hostel Entry Timings & Curfew", heading_style),
    Paragraph("Hostel gates for both Boys (Block A & B) and Girls (Block C & D) will close strictly at 8:30 PM on weekdays and 9:00 PM on weekends. Late entry requests must be pre-approved by Warden.", body_style),
    Paragraph("Section 2: Hostel Mess Fee & Menu", heading_style),
    Paragraph("Monthly mess fee is Rs. 4,500 payable by the 5th of every month. Breakfast is served from 7:30 AM to 9:00 AM, Lunch from 12:15 PM to 1:45 PM, and Dinner from 7:30 PM to 9:00 PM.", body_style),
    PageBreak(),
    Paragraph("Section 3: Campus Bus Routes & Schedule", heading_style),
    Paragraph("Bus Route 1 (Central Station to Campus): Departs at 7:15 AM, 7:45 AM, and 8:15 AM. Bus Route 2 (Airport Bus Stand to Campus): Departs at 7:30 AM and 8:00 AM. Evening return buses leave campus at 4:45 PM and 6:00 PM.", body_style),
    Paragraph("Section 4: Transport Pass Renewal", heading_style),
    Paragraph("Bus transport passes cost Rs. 12,000 per semester. Renewal must be completed at the Transport Office near Gate 2 before July 20, 2026.", body_style)
]
doc4.build(story4)

# 5. Merit_Scholarship_and_Financial_Aid.pdf
doc5 = SimpleDocTemplate("sample_docs/Merit_Scholarship_and_Financial_Aid.pdf", pagesize=letter)
story5 = [
    Paragraph("OFFICE OF STUDENT WELFARE & SCHOLARSHIPS", title_style),
    Paragraph("Merit Scholarship Policy & Financial Support Schemes 2026", body_style),
    Spacer(1, 10),
    Paragraph("Section 1: Institutional Merit Scholarship", heading_style),
    Paragraph("Top 5% students in each department securing CGPA of 9.0 and above are eligible for 50% tuition fee waiver under the Dean's Merit Scholarship Scheme. Applications open on August 10, 2026.", body_style),
    Paragraph("Section 2: Economically Weaker Section (EWS) Financial Aid", heading_style),
    Paragraph("Students with annual family income below Rs. 2.5 Lakhs can apply for full tuition fee waiver. Income certificate issued by Tahsildar must be submitted before August 30, 2026.", body_style),
    PageBreak(),
    Paragraph("Section 3: Sports & Extracurricular Excellence Award", heading_style),
    Paragraph("Students representing the University at National or State level sports competitions are eligible for 25% fee concession and special attendance relaxation up to 15%.", body_style),
    Paragraph("Section 4: Contact & Submission Desk", heading_style),
    Paragraph("All scholarship forms must be submitted physically at Room 104, Admin Block, or emailed to scholarships@nexus.edu.in before September 1, 2026.", body_style)
]
doc5.build(story5)

print("Successfully generated 5 campus PDF documents in sample_docs/")
