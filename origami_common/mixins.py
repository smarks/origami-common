class ActivePageMixin:
    """Mixin that adds active_page to context from class attribute."""

    active_page = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.active_page:
            context["active_page"] = self.active_page
        return context
