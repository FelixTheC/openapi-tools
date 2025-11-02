import typing

from django.db import IntegrityError
from django.http import HttpResponse
from rest_framework import status as drf_status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from serializers import *


@api_view(["PUT", "POST"])
def update_pet(request):

    if request.method == "PUT":
        serializer = PetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=drf_status.HTTP_200_OK)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

    if request.method == "POST":
        serializer = PetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=drf_status.HTTP_200_OK)
        return Response(
            serializer.errors, status=drf_status.HTTP_405_METHOD_NOT_ALLOWED
        )


@api_view(["GET"])
def find_pets_by_status(request):

    if request.method == "GET":

        serializer = FindPetsByStatusSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

        data = {}

        serializer = PetSerializer(data)
        return Response(serializer.data)


@api_view(["GET"])
def find_pets_by_tags(request):

    if request.method == "GET":

        serializer = FindPetsByTagsSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

        data = {}

        serializer = PetSerializer(data)
        return Response(serializer.data)


@api_view(["GET", "POST", "DELETE"])
def get_pet_by_id(request, pet_id: int):

    if request.method == "GET":
        data = {}
        serializer = PetSerializer(data)
        return Response(serializer.data)

    if request.method == "POST":
        serializer = UpdatePetWithFormSerializer(data=request.query_params)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=drf_status.HTTP_200_OK)
        return Response(
            serializer.errors, status=drf_status.HTTP_405_METHOD_NOT_ALLOWED
        )

    if request.method == "DELETE":
        # TODO replace me
        obj = Serializer()
        try:
            obj.delete()
        except IntegrityError:
            return HttpResponse(status=drf_status.HTTP_400_BAD_REQUEST)
        else:
            return HttpResponse(status=drf_status.HTTP_200_OK)


@api_view(["POST"])
def upload_file(request, pet_id: int):

    if request.method == "POST":
        serializer = UploadFileSerializer(data=request.query_params)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=drf_status.HTTP_200_OK)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def get_inventory(request):

    if request.method == "GET":
        data = {}
        serializer = Serializer(data)
        return Response(serializer.data)


@api_view(["POST"])
def place_order(request):

    if request.method == "POST":
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=drf_status.HTTP_200_OK)
        return Response(
            serializer.errors, status=drf_status.HTTP_405_METHOD_NOT_ALLOWED
        )


@api_view(["GET", "DELETE"])
def get_order_by_id(request, order_id: int):

    if request.method == "GET":
        data = {}
        serializer = OrderSerializer(data)
        return Response(serializer.data)

    if request.method == "DELETE":
        # TODO replace me
        obj = Serializer()
        try:
            obj.delete()
        except IntegrityError:
            return HttpResponse(status=drf_status.HTTP_400_BAD_REQUEST)
        else:
            return HttpResponse(status=drf_status.HTTP_200_OK)


@api_view(["POST"])
def create_user(request):

    if request.method == "POST":
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=drf_status.HTTP_200_OK)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def create_users_with_list_input(request):

    if request.method == "POST":
        serializer = Serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=drf_status.HTTP_200_OK)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def login_user(request):

    if request.method == "GET":

        serializer = LoginUserSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

        data = {}

        serializer = Serializer(data)
        return Response(serializer.data)


@api_view(["GET"])
def logout_user(request):
    pass


@api_view(["GET", "PUT", "DELETE"])
def get_user_by_name(request, username: str):

    if request.method == "GET":
        data = {}
        serializer = UserSerializer(data)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=drf_status.HTTP_200_OK)
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        # TODO replace me
        obj = Serializer()
        try:
            obj.delete()
        except IntegrityError:
            return HttpResponse(status=drf_status.HTTP_400_BAD_REQUEST)
        else:
            return HttpResponse(status=drf_status.HTTP_200_OK)
