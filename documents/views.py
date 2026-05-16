from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render

from .forms import UserDocumentForm
from .models import UserDocument


@login_required
def document_list(request):
    documents = UserDocument.objects.filter(
        user=request.user
    ).order_by("-uploaded_at")

    return render(
        request,
        "documents/document_list.html",
        {
            "documents": documents,
        },
    )


@login_required
def document_upload(request):
    if request.method == "POST":
        form = UserDocumentForm(request.POST, request.FILES)

        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user
            document.original_filename = document.file.name
            document.save()

            messages.success(
                request,
                "Document uploaded successfully.",
            )
            return redirect("documents:document_list")
    else:
        form = UserDocumentForm()

    return render(
        request,
        "documents/document_upload.html",
        {
            "form": form,
        },
    )
