from typing import Any
from django.db.models.query import QuerySet
from django.shortcuts import render, get_object_or_404
from .models import Book, Author, BookInstance, Genre
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin,PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required

from catalog.forms import RenewBookForm
import datetime

# Create your views here.
def index(request):
    """View function for home page of site"""
    num_visits = request.session.get('num_visits',0)
    num_visits += 1
    request.session['num_visits'] = num_visits

    #Generate counts of some of the main objects
    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()

    #Available books (status='a')
    num_instances_available = BookInstance.objects.filter(status__exact = 'a').count()

    #The 'all()' is implied by default
    num_authors = Author.objects.count()
    num_genres = Genre.objects.count()

    contains_word = request.GET.get('book_contains','')
    num_books_containing_word = 0
    if contains_word != '':
        num_books_containing_word = Book.objects.filter(title__icontains = contains_word).count()

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_genres': num_genres,
        'num_books_containing_word': num_books_containing_word,
        'contains_word': contains_word,
        'num_visits': num_visits
    }

    #Render the HTML template index.html with the data in the context variable
    return render(request,'index.html',context=context)


class BookListView(generic.ListView):
    model = Book
    paginate_by = 10
    context_object_name = 'book_list'
    template_name = 'books/book_list.html'

    def get_queryset(self):
        #return Book.objects.filter(title__icontains='crime')[:5]  #Get 5 books containing the title war
        return Book.objects.all()
    
    def get_context_data(self, **kwargs):
        # call the base implementation first to get the context
        context = super(BookListView,self).get_context_data(**kwargs)

        #create any data and add it to the context
        context['some_data'] = 'This is just some data'
        return context
    
class BookDetailView(generic.DetailView):
    model = Book

class AuthorListView(generic.ListView):
    model = Author
    paginate_by = 10
    context_object_name = 'author_list'
    template_name = 'authors/author_list.html'

    def get_queryset(self):
        return Author.objects.all()
    

class AuthorDetailView(generic.DetailView):
    model = Author


class LoanedBooksByUserListView(LoginRequiredMixin,generic.ListView):
    """Generic class-based view listing books on loan to current user."""
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return (
            BookInstance.objects.filter(borrower=self.request.user)
            .filter(status__exact = 'o')
            .order_by('due_back')
        )
    
class BorrowedBooksLibrarianListView(PermissionRequiredMixin,generic.ListView):
    """Generic class-based view listing books on loan to the librarian"""
    permission_required = 'catalog.can_mark_returned'
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_librarian.html'
    paginate_by = 10

    def get_queryset(self):
        return(
            BookInstance.objects.filter(status__exact = 'o')
            .order_by('due_back')
        )

@login_required
@permission_required('catalog.can_mark_returned',raise_exception=True)
def renew_book_librarian(request, pk):
    book_instance = get_object_or_404(BookInstance,pk=pk)

    #If this is a POST request then process the Form data
    if request.method == 'POST':

        #Create a form instance and populate it with data from the request (binding)
        form = RenewBookForm(request.POST)

        #Check if the form is valid
        if form.is_valid():
            #process the data in form.cleaned_data as required (here we just write it to the model
            # due_back field)
            book_instance.due_back = form.cleaned_data['renewal_date']
            book_instance.save()

            #redirect to a new URL
            return HttpResponseRedirect(reverse('all-borrowed'))
    
    # If this is a GET or any other method
    else:
        proposed_renewal_date = datetime.date.today() + datetime.timedelta(weeks=3)
        form = RenewBookForm(initial={'renewal_date' : proposed_renewal_date})  #initial attribute is for prefilling the form

    context = {
        'form' : form,
        'book_instance' : book_instance,
    }

    return render(request,'catalog/book_renew_librarian.html', context)
