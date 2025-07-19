# PUBG Match Stats Web App

เว็บแอปสำหรับดูข้อมูลสถิติย้อนหลังของผู้เล่น PUBG, เปรียบเทียบผู้เล่นและทีม, และดูรายละเอียดแมตช์

## คุณสมบัติ

- ค้นหาข้อมูลผู้เล่น PUBG และดูแมตช์ย้อนหลัง
- แสดงรายละเอียดแมตช์, สถิติทีม, อันดับรวม
- เปรียบเทียบสถิติผู้เล่นและทีม
- UI สวยงาม ใช้งานง่าย

## วิธีติดตั้งและใช้งาน

### 1. ติดตั้ง Python และไลบรารีที่จำเป็น

```bash
pip install flask requests
```

### 2. ตั้งค่า PUBG API Key

- สมัครและขอ API Key ที่ [PUBG Developer Portal](https://developer.pubg.com/)
- แก้ไขไฟล์ `app.py` ที่บรรทัด `PUBG_API_KEY = "..."` ใส่คีย์ของคุณ

### 3. รันเซิร์ฟเวอร์ Flask

```bash
python app.py
```

- ระบบจะรันที่ http://localhost:5000/

### 4. เปิดเว็บเบราว์เซอร์

- เปิดไฟล์ `index.html` หรือเข้าผ่าน http://localhost:5000/

## โครงสร้างไฟล์หลัก

- `app.py` - Backend API (Flask)
- `index.html`, `more.html` - Frontend UI
- `README.md` - คู่มือการใช้งาน

## หมายเหตุ

- หากพบปัญหา `ModuleNotFoundError` ให้ติดตั้งไลบรารีที่ขาดด้วย `pip install ...`
- หาก API PUBG จำกัดการใช้งานหรือ KEY หมดอายุ ให้ขอใหม่ที่หน้า PUBG Developer

---

**สร้างโดย:**  
- ใช้ Flask + Requests (Python)
- HTML + Bootstrap + Chart.js (Frontend)
