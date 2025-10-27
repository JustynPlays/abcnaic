# PDF generation functionality temporarily disabled per user request
from io import BytesIO
# from reportlab.lib.pagesizes import letter
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import inch
# from reportlab.lib import colors
# from reportlab.lib.enums import TA_CENTER, TA_LEFT
# from datetime import datetime
# import os

def generate_vaccine_record_pdf(user_data, vaccine_records, logo_path=None):
    """
    Generate a PDF vaccine record for a user - TEMPORARILY DISABLED
    
    Args:
        user_data (dict): User information (name, email, etc.)
        vaccine_records (list): List of vaccine records
        logo_path (str, optional): Path to logo image. Defaults to None.
    
    Returns:
        BytesIO: In-memory PDF file
    """
    # PDF generation temporarily disabled - return empty buffer
    buffer = BytesIO()
    buffer.write(b"PDF generation temporarily disabled")
    buffer.seek(0)
    return buffer
#     doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
#                            topMargin=72, bottomMargin=72)
#     
#     # Custom styles
#     styles = getSampleStyleSheet()
#     
#     # Add styles only if they don't exist
#     if 'Center' not in styles:
#         styles.add(ParagraphStyle(
#             name='Center', 
#             alignment=TA_CENTER, 
#             fontSize=14, 
#             spaceAfter=20
#         ))
#     
#     if 'Title' not in styles:
#         styles.add(ParagraphStyle(
#             name='Title', 
#             fontSize=16, 
#             alignment=TA_CENTER, 
#             spaceAfter=30,
#             textColor=colors.HexColor('#2c3e50'),
#             fontName='Helvetica-Bold'
#         ))
#     
#     if 'Header' not in styles:
#         styles.add(ParagraphStyle(
#             name='Header', 
#             fontSize=12, 
#             alignment=TA_LEFT, 
#             spaceAfter=6,
#             textColor=colors.HexColor('#2c3e50'),
#             fontName='Helvetica-Bold'
#         ))
#     
#     if 'Normal_Left' not in styles:
#         styles.add(ParagraphStyle(
#             name='Normal_Left', 
#             fontSize=10, 
#             alignment=TA_LEFT, 
#             spaceAfter=12
#         ))
#     
#     # Start building the PDF
#     elements = []
#     
#     # Add logo if provided
#     if logo_path and os.path.exists(logo_path):
#         try:
#             logo = Image(logo_path, width=2*inch, height=1*inch)
#             logo.hAlign = 'CENTER'
#             elements.append(logo)
#             elements.append(Spacer(1, 20))
#         except:
#             pass  # Skip logo if there's an error loading it
#     
#     # Add title
#     elements.append(Paragraph("VACCINATION RECORD", styles['Title']))
#     
#     # Add user information
#     elements.append(Paragraph("PERSONAL INFORMATION", styles['Header']))
#     user_info = [
#         ["Name:", user_data.get('name', 'N/A')],
#         ["Date of Birth:", user_data.get('date_of_birth', 'N/A')],
#         ["Patient ID:", user_data.get('id', 'N/A')],
#         ["Date Issued:", datetime.now().strftime('%B %d, %Y')]
#     ]
#     
#     user_table = Table(user_info, colWidths=[1.5*inch, 4*inch])
#     user_table.setStyle(TableStyle([
#         ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
#         ('FONTSIZE', (0, 0), (-1, -1), 10),
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
#         ('TOPPADDING', (0, 0), (-1, -1), 3),
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
#         ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
#     ]))
#     elements.append(user_table)
#     elements.append(Spacer(1, 20))
#     
#     # Add vaccine records
#     elements.append(Paragraph("VACCINATION HISTORY", styles['Header']))
#     
#     if vaccine_records:
#         # Prepare table data
#         table_data = [
#             ["Vaccine", "Dose #", "Date Administered", "Administered By", "Location"]
#         ]
#         
#         for record in vaccine_records:
#             table_data.append([
#                 record.get('vaccine_name', 'N/A'),
#                 str(record.get('dose_number', 'N/A')),
#                 record.get('administered_date', 'N/A'),
#                 record.get('administered_by', 'N/A'),
#                 record.get('location', 'N/A')
#             ])
#         
#         # Create and style the table
#         col_widths = [1.5*inch, 0.7*inch, 1.2*inch, 1.5*inch, 1.5*inch]
#         record_table = Table(table_data, colWidths=col_widths, repeatRows=1)
#         record_table.setStyle(TableStyle([
#             ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
#             ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#             ('FONTSIZE', (0, 0), (-1, -1), 8),
#             ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
#             ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
#             ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
#             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
#         ]))
#         
#         # Add zebra striping
#         for i in range(1, len(table_data)):
#             if i % 2 == 0:
#                 bg_color = colors.HexColor('#ffffff')
#             else:
#                 bg_color = colors.HexColor('#f8f9fa')
#             record_table.setStyle(TableStyle([
#                 ('BACKGROUND', (0, i), (-1, i), bg_color)
#             ]))
#         
#         elements.append(record_table)
#     else:
#         elements.append(Paragraph("No vaccination records found.", styles['Normal_Left']))
#     
#     # Add footer
#     elements.append(Spacer(1, 20))
#     elements.append(Paragraph(
#         "This is an official document. Unauthorized duplication is prohibited.", 
#         ParagraphStyle('Footer', fontSize=8, alignment=TA_CENTER, textColor=colors.gray)
#     ))
#     
#     # Build the PDF
#     doc.build(elements)
#     
#     # Reset buffer position to the beginning
#     buffer.seek(0)
#     return buffer

# PDF generation functionality has been temporarily disabled
# To re-enable, uncomment the code above and ensure reportlab is installed in requirements.txt
