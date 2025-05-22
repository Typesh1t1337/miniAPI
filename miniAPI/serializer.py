from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any


class BaseSerializer:
    def __init__(self, data):
        self.initial_data = data
        self.__validated_data = {}
        self.errors = {}
        self.__validation_checked = False

        self.declared_fields = self.__get_declared_fields()
        self.__validate()

    def __get_declared_fields(self):
        declared_fields = {
            name: field
            for name, field, in self.__class__.__dict__.items()
            if isinstance(field, Field)
        }

        return declared_fields

    @property
    def data(self):
        if self.__validation_checked:
            return self.__validated_data
        else:
            raise ValidationError(error="Field is not valid")

    def __validate(self):
        for name, field in self.declared_fields.items():
            if name in self.initial_data:
                value = self.initial_data[name]
            elif field.default is not None:
                value = field.default
            elif field.required:
                self.errors[name] = "Field is required"
                continue
            else:
                value = None

            try:
                validated = field.validate(value)
                self.__validated_data[name] = validated
            except Exception as e:
                self.errors[name] = str(e)

    def is_valid(self):
        self.__validation_checked = True
        return not self.errors

    def __getattr__(self, name):
        return f"{name} not exist"


class Field:
    def __init__(self, required: bool = True, default: Any = None):
        self.required = required
        self.default = default

    def validate(self, value):
        if value is None:
            if self.required:
                raise ValueError("Field is required")
            return self.default
        return self._validate_type(value)

    def _validate_type(self, value):
        raise NotImplementedError


class StringField(Field):

    def _validate_type(self, value):
        if not isinstance(value, str):
            raise TypeError('value must be string')

        return value


class IntegerField(Field):
    def _validate_type(self, value):
        if not isinstance(value, int):
            try:
                value = int(value)
            except ValueError:
                raise TypeError('value must be integer')

        return value


class FloatField(Field):
    def _validate_type(self, value):
        if not isinstance(value, float):
            try:
                value = float(value)
            except ValueError:
                raise TypeError('value must be float')

            return value


class BooleanField(Field):
    def _validate_type(self, value):
        if not isinstance(value, bool):
            raise TypeError('value must be boolean')


class DateField(Field):
    def validate(self, value):
        if not isinstance(value, date):
            raise TypeError('value must be date')


class DateTimeField(Field):
    def _validate_type(self, value):
        if not isinstance(value, datetime):
            raise TypeError('value must be datetime')


class DecimalField(Field):
    def _validate_type(self, value):
        if not isinstance(value, Decimal):
            try:
                value = Decimal(value)
            except ValueError:
                raise TypeError('value must be Decimal')

        return value


class JSONField(Field):
    def _validate_type(self, value):
        if not isinstance(value, (dict, list)):
            raise TypeError('value must be JSON')

        return value


class ValidationError(Exception):
    def __init__(self, error):
        self.error = error
        super().__init__("Validation Error")


class UserSerializer(BaseSerializer):
    username = StringField(required=True, default="Lox")
    email = FloatField(required=True)


