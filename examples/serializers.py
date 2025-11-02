from rest_framework import serializers


class LoginUserSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class UploadFileSerializer(serializers.Serializer):
    additionalmetadata = serializers.CharField()


class UpdatePetWithFormSerializer(serializers.Serializer):
    name = serializers.CharField()
    status = serializers.CharField()


class FindPetsByStatusSerializer(serializers.Serializer):
    status = serializers.CharField()


class ApiResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    type = serializers.CharField()
    message = serializers.CharField()


class TagSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField()
    phone = serializers.CharField()
    userstatus = serializers.IntegerField()


class CategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class AddressSerializer(serializers.Serializer):
    street = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    zip = serializers.CharField()


class OrderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    petid = serializers.IntegerField()
    quantity = serializers.IntegerField()
    shipdate = serializers.DateTimeField()
    status = serializers.CharField()
    complete = serializers.BooleanField()


class CustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    address = AddressSerializer(many=True)


class PetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    category = CategorySerializer()
    photourls = serializers.CharField()
    tags = TagSerializer(many=True)
    status = serializers.CharField()


class FindPetsByTagsSerializer(serializers.Serializer):
    tags = serializers.CharField()
