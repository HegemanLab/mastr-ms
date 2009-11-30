from madas.repository.models import *
from django.contrib import admin

class OrganAdmin(admin.ModelAdmin):
    list_display = ('name', 'detail')
    search_fields = ['name']

class BiologicalSourceAdmin(admin.ModelAdmin):
    list_display = ('type',)

class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'comment')
    search_fields = ['title']

class ExperimentStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ['name']

class AnimalAdmin(admin.ModelAdmin):
    list_display = ('sex', 'age', 'parental_line')

class TreatmentAdmin(admin.ModelAdmin):
    list_display = ('name','description')

class SampleAdmin(admin.ModelAdmin):
    list_display = ('label','comment', 'sample_class')

class SampleTimelineAdmin(admin.ModelAdmin):
    list_display = ('taken_on','taken_at')

class StandardOperationProcedureAdmin(admin.ModelAdmin):
    list_display = ('responsible', 'label', 'area_where_valid', 'comment', 'organisation', 'version', 'defined_by', 'replaces_document', 'content', 'attached_pdf')

class OrganismTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    
class UserExperimentAdmin(admin.ModelAdmin):
    list_display = ('user', 'experiment', 'type')   

class UserInvolvementTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')   

class PlantAdmin(admin.ModelAdmin):
    list_display = ('id', 'development_stage')
    
class SampleClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'biological_source', 'organ')
    

admin.site.register(OrganismType, OrganismTypeAdmin)
admin.site.register(UserInvolvementType, UserInvolvementTypeAdmin)
admin.site.register(Organ, OrganAdmin)
admin.site.register(BiologicalSource, BiologicalSourceAdmin)
admin.site.register(Experiment, ExperimentAdmin)
admin.site.register(ExperimentStatus, ExperimentStatusAdmin)
admin.site.register(Animal, AnimalAdmin)
admin.site.register(Treatment, TreatmentAdmin)
admin.site.register(Sample,SampleAdmin)
admin.site.register(SampleTimeline,SampleTimelineAdmin)
admin.site.register(StandardOperationProcedure,StandardOperationProcedureAdmin)
admin.site.register(UserExperiment,UserExperimentAdmin)
admin.site.register(Plant, PlantAdmin)
admin.site.register(SampleClass, SampleClassAdmin)
