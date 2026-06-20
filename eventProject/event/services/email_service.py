"""
Email service for event booking notifications.
Handles booking confirmations, invoice delivery, reminders, and cancellations.
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_booking_confirmation_email(booking, invoice_pdf=None):
    """
    Send booking confirmation email to the user.
    
    Args:
        booking: Booking instance
        invoice_pdf: Optional PDF file path for invoice attachment
    """
    try:
        context = {
            'user_name': booking.user.first_name or booking.user.username,
            'event_title': booking.event.title,
            'event_date': booking.event.event_date,
            'event_time': booking.event.start_time,
            'venue': booking.event.venue,
            'city': booking.event.city.name,
            'quantity': booking.quantity,
            'price_per_ticket': booking.ticket.price,
            'total_price': booking.total_price,
            'booking_reference': booking.booking_reference,
            'download_link': f"{settings.SITE_URL}/invoice/{booking.booking_reference}/download/" if hasattr(settings, 'SITE_URL') else '/invoice/{booking.booking_reference}/download/',
        }
        
        html_message = render_to_string('event/emails/booking_confirmation.html', context)
        text_message = render_to_string('event/emails/booking_confirmation.txt', context)
        
        email = EmailMultiAlternatives(
            subject=f'Booking Confirmation - {booking.event.title}',
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[booking.user.email]
        )
        email.attach_alternative(html_message, "text/html")
        
        # Attach invoice PDF if provided
        if invoice_pdf:
            with open(invoice_pdf, 'rb') as attachment:
                email.attach(f"invoice_{booking.booking_reference}.pdf", attachment.read(), "application/pdf")
        
        email.send(fail_silently=False)
        logger.info(f"Booking confirmation email sent to {booking.user.email} for booking {booking.booking_reference}")
        
    except Exception as e:
        logger.error(f"Error sending booking confirmation email: {str(e)}")
        raise


def send_invoice_email(booking, invoice_pdf_path):
    """
    Send invoice via email to the user.
    
    Args:
        booking: Booking instance
        invoice_pdf_path: Path to the PDF invoice file
    """
    try:
        context = {
            'user_name': booking.user.first_name or booking.user.username,
            'booking_reference': booking.booking_reference,
            'event_title': booking.event.title,
            'total_price': booking.total_price,
        }
        
        html_message = render_to_string('event/emails/invoice_email.html', context)
        text_message = render_to_string('event/emails/invoice_email.txt', context)
        
        email = EmailMultiAlternatives(
            subject=f'Invoice - {booking.event.title}',
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[booking.user.email]
        )
        email.attach_alternative(html_message, "text/html")
        
        # Attach the PDF invoice
        with open(invoice_pdf_path, 'rb') as attachment:
            email.attach(f"invoice_{booking.booking_reference}.pdf", attachment.read(), "application/pdf")
        
        email.send(fail_silently=False)
        logger.info(f"Invoice email sent to {booking.user.email} for booking {booking.booking_reference}")
        
    except Exception as e:
        logger.error(f"Error sending invoice email: {str(e)}")
        raise


def send_event_reminder_email(booking):
    """
    Send event reminder email 24 hours before the event.
    
    Args:
        booking: Booking instance
    """
    try:
        context = {
            'user_name': booking.user.first_name or booking.user.username,
            'event_title': booking.event.title,
            'event_date': booking.event.event_date,
            'event_time': booking.event.start_time,
            'venue': booking.event.venue,
            'city': booking.event.city.name,
            'booking_reference': booking.booking_reference,
            'quantity': booking.quantity,
        }
        
        html_message = render_to_string('event/emails/event_reminder.html', context)
        text_message = render_to_string('event/emails/event_reminder.txt', context)
        
        email = EmailMultiAlternatives(
            subject=f'Reminder: {booking.event.title} is tomorrow!',
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[booking.user.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        logger.info(f"Event reminder email sent to {booking.user.email} for event {booking.event.title}")
        
    except Exception as e:
        logger.error(f"Error sending event reminder email: {str(e)}")
        raise


def send_cancellation_email(booking):
    """
    Send cancellation confirmation email.
    
    Args:
        booking: Booking instance
    """
    try:
        context = {
            'user_name': booking.user.first_name or booking.user.username,
            'event_title': booking.event.title,
            'booking_reference': booking.booking_reference,
            'quantity': booking.quantity,
            'refund_amount': booking.total_price,
        }
        
        html_message = render_to_string('event/emails/cancellation_confirmation.html', context)
        text_message = render_to_string('event/emails/cancellation_confirmation.txt', context)
        
        email = EmailMultiAlternatives(
            subject=f'Booking Cancelled - {booking.event.title}',
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[booking.user.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        logger.info(f"Cancellation email sent to {booking.user.email} for booking {booking.booking_reference}")
        
    except Exception as e:
        logger.error(f"Error sending cancellation email: {str(e)}")
        raise


def get_upcoming_event_bookings():
    """
    Get all bookings for events happening tomorrow.
    Used for sending event reminder emails.
    """
    from datetime import datetime, timedelta
    from ..models import Booking
    
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    return Booking.objects.filter(
        event__event_date=tomorrow,
        status='confirmed'
    ).select_related('user', 'event')
