# compliance/inspection_schedules.py
from datetime import date, time

from compliance.registry import InspectionScheduleInterface, InspectionScheduleRegistry
from django_stratagem import (
    ConditionalInterface,
    DateRangeCondition,
    FeatureFlagCondition,
    GroupCondition,
    TimeWindowCondition,
)


class StandardSchedule(InspectionScheduleInterface):
    slug = "standard"
    description = "Regular inspection schedule - available any time"
    priority = 10

    def get_next_inspection(self, subcontractor):
        return date.today()


class BusinessHoursSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "business_hours"
    description = "Inspections during business hours only (Mon-Fri, 9am-5pm)"
    priority = 20
    condition = TimeWindowCondition(time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])

    def get_next_inspection(self, subcontractor):
        return date.today()


class SummerBlitzSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "summer_blitz"
    description = "Accelerated summer inspection campaign (Jun-Aug)"
    priority = 30
    condition = DateRangeCondition(date(2026, 6, 1), date(2026, 8, 31))

    def get_next_inspection(self, subcontractor):
        return date.today()


class SmartSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "smart_schedule"
    description = "AI-powered risk-based scheduling (beta)"
    priority = 40
    condition = FeatureFlagCondition("smart_scheduling_beta")

    def get_next_inspection(self, subcontractor):
        return date.today()


class ManagerSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "manager_only"
    description = "Manager-defined custom schedule"
    priority = 50
    condition = GroupCondition("project_managers")

    def get_next_inspection(self, subcontractor):
        return date.today()


class SummerBusinessHoursSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "summer_business_hours"
    description = "Business hours inspections during summer peak"
    priority = 35
    condition = (
        TimeWindowCondition(time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])
        & DateRangeCondition(date(2026, 6, 1), date(2026, 8, 31))
    )

    def get_next_inspection(self, subcontractor):
        return date.today()
