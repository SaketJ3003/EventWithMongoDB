from django.shortcuts import render
from django.http import FileResponse, HttpResponse
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Event, Booking
from .serializers import ExtraImagesResponseSerializer, FeatureImageSerializer, EventImageSerializer
from .services.invoice_service import generate_invoice_pdf
from io import BytesIO
import os
import tempfile


class FeatureImageUploadView(APIView):

    permission_classes = [IsAdminUser]
    parser_classes     = [MultiPartParser, FormParser]

    def patch(self, request, event_id):
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Event not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if len(request.FILES.getlist('feature_image')) > 1:
            return Response(
                {'success': False, 'message': 'Only one feature image is allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = FeatureImageSerializer(event, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            if event.feature_image:
                event.feature_image.delete(save=False)
            serializer.save()
            response_serializer = FeatureImageSerializer(event, context={'request': request})
            return Response(
                {
                    'success': True,
                    'message': 'Feature image uploaded successfully.',
                    'data': response_serializer.data,
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class ExtraImagesUploadView(APIView):
    
    permission_classes = [IsAdminUser]
    parser_classes     = [MultiPartParser, FormParser]

    def get(self, request, event_id):
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Event not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {'success': True, 'data': ExtraImagesResponseSerializer(event, context={'request': request}).data},
            status=status.HTTP_200_OK
        )

    def post(self, request, event_id):
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Event not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        files = request.FILES.getlist('images')
        if not files:
            return Response(
                {'success': False, 'message': 'No images provided. Use field key "images".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created = []
        errors  = []
        for f in files:
            serializer = EventImageSerializer(data={'image': f}, context={'request': request})
            if serializer.is_valid():
                img_obj = serializer.save()
                event.extraImages.add(img_obj)
                created.append(serializer.data)
            else:
                errors.append({f.name: serializer.errors})

        if errors:
            return Response(
                {
                    'success': False,
                    'message': 'Some images failed validation.',
                    'uploaded': created,
                    'errors': errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                'success': True,
                'message': f'{len(created)} image(s) uploaded successfully.',
                'data': ExtraImagesResponseSerializer(event, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED
        )
    

def login_page(request):
    return render(request, 'event/login.html')


def signup_page(request):
    return render(request, 'event/signup.html')


def event_list_page(request):
    return render(request, 'event/event_list.html')


def event_detail_page(request, slug):
    return render(request, 'event/event_detail.html')


class DownloadInvoiceView(View):
    """Download invoice PDF for a booking"""
    
    def get(self, request, booking_reference):
        try:
            booking = Booking.objects.get(booking_reference=booking_reference)
        except Booking.DoesNotExist:
            return HttpResponse("Booking not found", status=404)
        
        # Check if user has permission to download this invoice
        if request.user.is_authenticated and request.user != booking.user:
            if not (request.user.is_staff or request.user.is_superuser):
                return HttpResponse("You don't have permission to download this invoice", status=403)
        
        # Generate PDF
        pdf_buffer = generate_invoice_pdf(booking)
        
        # Return PDF as response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{booking_reference}.pdf"'
        
        return response

