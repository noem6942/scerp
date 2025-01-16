'''
time_app/serializers.py
'''
from rest_framework import serializers


class HourlyRateSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    currency = serializers.CharField()


class MembershipSerializer(serializers.Serializer):
    userId = serializers.CharField()
    hourlyRate = serializers.FloatField(allow_null=True)
    costRate = serializers.FloatField(allow_null=True)
    targetId = serializers.CharField()
    membershipType = serializers.CharField()
    membershipStatus = serializers.CharField()


class EstimateSerializer(serializers.Serializer):
    estimate = serializers.CharField()
    type = serializers.CharField()


class TimeEstimateSerializer(serializers.Serializer):
    estimate = serializers.CharField()
    type = serializers.CharField()
    resetOption = serializers.CharField(allow_null=True)
    active = serializers.BooleanField()
    includeNonBillable = serializers.BooleanField()


class ProjectSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    hourlyRate = HourlyRateSerializer()
    clientId = serializers.CharField(allow_blank=True)
    workspaceId = serializers.CharField()
    billable = serializers.BooleanField()
    memberships = MembershipSerializer(many=True)
    color = serializers.CharField()
    estimate = EstimateSerializer()
    archived = serializers.BooleanField()
    duration = serializers.CharField()
    clientName = serializers.CharField(allow_blank=True)
    note = serializers.CharField(allow_blank=True)
    costRate = serializers.FloatField(allow_null=True)
    timeEstimate = TimeEstimateSerializer()
    budgetEstimate = serializers.JSONField(allow_null=True)
    estimateReset = serializers.JSONField(allow_null=True)
    template = serializers.BooleanField()
    public = serializers.BooleanField()


class TimeIntervalSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    duration = serializers.CharField()


class TimeEntrySerializer(serializers.Serializer):
    id = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    tagIds = serializers.ListField(child=serializers.CharField(), allow_null=True)
    userId = serializers.CharField()
    billable = serializers.BooleanField()
    taskId = serializers.CharField(allow_null=True)
    projectId = serializers.CharField(allow_null=True)
    workspaceId = serializers.CharField()
    timeInterval = TimeIntervalSerializer()
    customFieldValues = serializers.JSONField()
    type = serializers.CharField()
    kioskId = serializers.CharField(allow_null=True)
    hourlyRate = HourlyRateSerializer()
    costRate = HourlyRateSerializer()
    isLocked = serializers.BooleanField()

