from django import forms

from companies.models import Company, PeerGroupProposal


class PeerGroupForm(forms.Form):
    selected_peers = forms.ModelMultipleChoiceField(
        queryset=Company.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )
    confirm = forms.BooleanField(required=False)

    def __init__(self, *, proposal: PeerGroupProposal, data=None, **kwargs):
        super().__init__(data=data, **kwargs)
        self.proposal = proposal
        self.fields["selected_peers"].queryset = Company.objects.exclude(pk=proposal.company_id)

    def clean_selected_peers(self):
        peers = self.cleaned_data["selected_peers"]
        if self.proposal.company_id in {peer.pk for peer in peers}:
            raise forms.ValidationError("The selected company cannot be its own peer.")
        return peers

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("confirm"):
            selected_count = len(cleaned.get("selected_peers", ()))
            minimum_met = selected_count >= self.proposal.minimum_candidates
            insufficient_rule = not self.proposal.sufficient_universe and selected_count == self.proposal.eligible_count
            if not minimum_met and not insufficient_rule:
                raise forms.ValidationError(
                    f"Confirm at least {self.proposal.minimum_candidates} peers, or select the complete insufficient universe."
                )
        return cleaned
