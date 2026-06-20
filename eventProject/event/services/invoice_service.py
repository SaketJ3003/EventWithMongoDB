"""
PDF Invoice generation service using ReportLab.
Creates professional invoices with QR codes for ticket verification.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import qrcode
import os
from django.conf import settings


def generate_invoice_pdf(booking):
    """
    Generate a professional PDF invoice for a booking.
    
    Args:
        booking: Booking instance
        
    Returns:
        BytesIO object containing the PDF
    """
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#09090b'),
        spaceAfter=10,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#71717a'),
        spaceAfter=10,
        textTransform='uppercase',
        letterSpacing=1.5,
        fontName='Helvetica-Bold',
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#18181b'),
        leading=16,
    )
    
    # Header
    title = Paragraph("INVOICE", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    # Company and Invoice Info
    info_data = [
        [
            Paragraph(f"<b>EVENTHUB</b><br/><font color='#71717a'>www.eventhub.com</font>", normal_style),
            Paragraph(
                f"<font color='#71717a'>Invoice No:</font> <b>{booking.booking_reference}</b><br/>"
                f"<font color='#71717a'>Date:</font> {booking.created_at.strftime('%B %d, %Y')}<br/>"
                f"<font color='#71717a'>Status:</font> {booking.status.upper()}",
                ParagraphStyle('RightAlign', parent=normal_style, alignment=TA_RIGHT)
            ),
        ]
    ]
    
    info_table = Table(info_data, colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e4e4e7')),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Bill To section
    bill_to_heading = Paragraph("BILL TO", heading_style)
    elements.append(bill_to_heading)
    
    customer_info = Paragraph(
        f"<b>{booking.user.get_full_name() or booking.user.username}</b><br/>"
        f"{booking.user.email}<br/>"
        f"<font color='#71717a'>Event Attendee</font>",
        normal_style
    )
    elements.append(customer_info)
    elements.append(Spacer(1, 0.4*inch))
    
    # Event Details Table
    event_data = [
        ['Event Details', '', ''],
        ['Event', booking.event.title, ''],
        ['Date', booking.event.event_date.strftime('%B %d, %Y'), ''],
        ['Time', booking.event.start_time.strftime('%I:%M %p'), ''],
        ['Venue', booking.event.venue, ''],
        ['Location', f"{booking.event.city.name}, {booking.event.state.name}", ''],
    ]
    
    event_table = Table(event_data, colWidths=[1.5*inch, 3.5*inch, 2*inch])
    event_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#09090b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#ffffff')),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fafafa')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#18181b')),
        ('LINEBELOW', (0, 1), (-1, -1), 1, colors.HexColor('#e4e4e7')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(event_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Ticket Information Table
    ticket_data = [
        ['Description', 'Unit Price', 'Quantity', 'Amount'],
        [
            f'Ticket - {booking.event.title}',
            f'Rs.{booking.ticket.price}',
            f'{booking.quantity}',
            f'Rs.{booking.total_price}'
        ],
        ['', '', 'Total:', f'Rs.{booking.total_price}'],
    ]
    
    ticket_table = Table(ticket_data, colWidths=[3.5*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    ticket_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#09090b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#ffffff')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('LINEBELOW', (0, 1), (-1, -2), 1, colors.HexColor('#e4e4e7')),
        ('ALIGN', (2, -1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (2, -1), (-1, -1), 12),
        ('TEXTCOLOR', (2, -1), (-1, -1), colors.HexColor('#18181b')),
        ('TOPPADDING', (2, -1), (-1, -1), 15),
        ('BOTTOMPADDING', (2, -1), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    elements.append(ticket_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # QR Code section
    qr_data = f"BookingRef:{booking.booking_reference}|Event:{booking.event.title}|User:{booking.user.email}"
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    qr_img = Image(qr_buffer, width=1.0*inch, height=1.0*inch)
    
    qr_data = [
        [qr_img, Paragraph(
            f"<b>Booking Reference</b><br/><font size=16 color='#09090b'><b>{booking.booking_reference}</b></font><br/><br/>"
            f"<font color='#71717a'>Please present this QR code at the event for entry verification.</font>",
            normal_style
        )]
    ]
    
    qr_table = Table(qr_data, colWidths=[1.2*inch, 5.8*inch])
    qr_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (0, 0), 15),
    ]))
    
    elements.append(qr_table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Footer
    footer = Paragraph(
        f"<font size=9 color='#a1a1aa'>Thank you for your booking! For any inquiries, please contact support@eventhub.com<br/>"
        f"© 2026 EventHub. All rights reserved.</font>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)
    )
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


def save_invoice_to_file(booking, filepath):
    """
    Generate and save invoice PDF to a file.
    
    Args:
        booking: Booking instance
        filepath: File path where to save the PDF
    """
    pdf_buffer = generate_invoice_pdf(booking)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'wb') as f:
        f.write(pdf_buffer.getvalue())
    
    return filepath
