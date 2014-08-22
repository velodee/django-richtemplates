# encoding: UTF-8

from django import forms
from django.db import models

from richtemplates import settings as richtemplates_settings
from richtemplates.utils import get_fk_fields, get_user_profile_model
from richtemplates.skins import get_skins
from richtemplates.fields import RestructuredTextAreaField, UserByNameField,\
    ModelByNameField
from richtemplates.widgets import RichCheckboxSelectMultiple

__all__ = ['RestructuredTextAreaField', 'UserByNameField', 'ModelByNameField',
    'LimitingModelFormError', 'LimitingModelForm', 'RichCheckboxSelectMultiple']

# =================================== #
# Limiting choices ModelForm subclass #
# =================================== #

class LimitingModelFormError(Exception):
    pass

class LimitingModelForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(LimitingModelForm, self).__init__(*args, **kwargs)
        self._meta.choices_limiting_models = self._get_limiting_model_fields()
        self._limit_querysets()

    def _get_limiting_model_fields(self):
        """
        Returns model's field instances that should limit querysets of
        other fields at this form.
        """
        limiting_field_names = getattr(self.Meta, 'choices_limiting_fields', [])
        limiting_fields, limiting_models = [], []
        # Support related attributes a__b__c
        model = self._meta.model
        for fieldname in limiting_field_names:
            # if fieldname is a__b__c, just save c
            # and keep the fullname is a__b__c for later access
            for bit in fieldname.split('__'):
                field = model._meta.get_field_by_name(bit)[0]
                if not isinstance(field, models.ForeignKey):
                    raise LimitingModelFormError("Choices limiting field should "
                        "be an instance of django.db.models.ForeignKey")
                model = field.related.parent_model
                if model in limiting_models:
                    raise LimitingModelFormError("Cannot limit choices using "
                        "foreign keyed model more than once. Crashed at field "
                        "'%s'" % (field.name))
            field.fullname = fieldname  # keep it for later use
            limiting_models.append(model)
            limiting_fields.append(field)

        return limiting_fields

    def _limit_querysets(self):
        """
        Limits querysets of the fields using
        self._meta.choices_limiting_fields.
        """

        for model_field in self._meta.choices_limiting_models:
            limiting_model = model_field.related.parent_model
            for bfield in self:
                field = bfield.field
                if not isinstance(field, forms.ModelChoiceField):
                    continue

                model_to_check = field.queryset.model
                fk_fields = get_fk_fields(model_to_check, limiting_model)

                if len(fk_fields) > 1:
                    raise LimitingModelFormError("Too many fk'd fields")
                elif fk_fields and limiting_model is fk_fields[0].related.parent_model:
                    try:
                        # Support related attributes a__b__c
                        limit_to = self.instance
                        for bit in model_field.fullname.split('__'):
                            try:
                                limit_to = getattr(limit_to, bit)
                            except Exception:
                                # Mostly DoesNotExist exception. TODO: catch exact exception
                                # Example: getattr(task_revision, 'task') expected to return the task.
                                # But if task_revision.pk = None, there's no task associate with it.
                                # So the Task.DoesNotExist will be raised.
                                # Question: if task_revision.pk = None, is there any case that the task is exist.
                                # Answer: Yes. When the form is initialized with instance. i.e. Form(instance=instance)
                                pass
                        if limit_to.pk:
                            # The form must exclude the fields which specified in choices_limiting_fields.
                            # Otherwise the next queryset will fail due to it can not find the correct field in model.
                            # This is normal usecase. But sometimes we need to edit this field in the admin page.
                            # So simply ignore the field which has same model with the queryset
                            if isinstance(limit_to, model_to_check):
                                continue
                            field.queryset = field.queryset\
                                .filter(**{model_field.name: limit_to})
                    except limiting_model.DoesNotExist:
                        raise LimitingModelFormError("Tried to limit field "
                            "'%s' but it's instance field is empty"
                            % model_field.name)


# =================================== #
# Richtemplates user profiles helpers #
# =================================== #

class RichSkinChoiceField(forms.ChoiceField):
    """
    Use this field for a user profile form if you want to allow users to
    set their default skin.
    """
    def __init__(self, *args, **kwargs):
        super(RichSkinChoiceField, self).__init__(*args, **kwargs)
        self.choices = [(skin.alias, skin.name) for skin in get_skins()]

class RichCodeStyleChoiceField(forms.ChoiceField):
    """
    Use this field for user profile form if you want to allow users to set
    their code style used by pygments to highlight code snipppets.
    """
    def __init__(self, *args, **kwargs):
        super(RichCodeStyleChoiceField, self).__init__(*args, **kwargs)
        self.choices = [(alias, alias.title()) for alias in
            sorted(richtemplates_settings.REGISTERED_PYGMENTS_STYLES.keys())]

class UserProfileForm(forms.ModelForm):
    skin = RichSkinChoiceField()
    code_style = RichCodeStyleChoiceField()

    class Meta:
        exclude = ('user',)
        model = get_user_profile_model()

