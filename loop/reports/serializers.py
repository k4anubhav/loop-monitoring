from rest_framework import serializers


class ReportIdSerializer(serializers.Serializer):
    report_id = serializers.UUIDField(read_only=True)

    def update(self, instance, validated_data):
        raise Exception('Not allowed')

    def create(self, validated_data):
        raise Exception('Not allowed')


class ReportSerializer(serializers.Serializer):
    report_id = serializers.UUIDField(write_only=True)
    status = serializers.ChoiceField(choices=['failed', 'running', 'completed'], read_only=True)
    report = serializers.FileField(required=False, read_only=True)

    def update(self, instance, validated_data):
        raise Exception('Not allowed')

    def create(self, validated_data):
        raise Exception('Not allowed')
