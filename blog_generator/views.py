from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
from pytube import YouTube
import os
import assemblyai as aai
import openai
import re



# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

YT_REGEX = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data.get('link', '').strip()

            # Validate the link
            if not yt_link or not YT_REGEX.match(yt_link):
                return JsonResponse({'error': 'Invalid YouTube link'}, status=400)

        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error_message':'Invalid data sent'}, status=400) 

        try:
            # Step 1: Get title
            print("DEBUG yt_link:", yt_link)
            title = yt_title(yt_link)
            print("✅ Got video title:", title)

            if not title:   # this checks for None OR empty string
                return JsonResponse(
                    {'error': "Could not fetch YouTube title"},
                        status=400
                )

            # Step 2: Get transcription
            transcription = get_transcription(yt_link)
            if not transcription:
                print("❌ Transcription failed")
                return JsonResponse({'error': "Failed to get transcript"}, status=500)
            print("✅ Got transcription")

            # Step 3: Generate blog
            blog_content = generate_blog_from_transcription(transcription)
            if not blog_content:
                print("❌ Blog generation failed")
                return JsonResponse({'error': "Failed to generate blog article"}, status=500)
            print("✅ Blog generated")

            return JsonResponse({'content': blog_content})

        except Exception as e:
            import traceback
            print("❌ Error in generate_blog:", str(e))
            traceback.print_exc()
            return JsonResponse({'error': f"Server error: {str(e)}"}, status=500)

    return JsonResponse({'error_message': 'Invalid request method'}, status=405)
    
def yt_title(link):
    try:
        print("🔎 Trying to fetch YouTube title for:", link)
        yt = YouTube(link)
        print("✅ Successfully created YouTube object")
        return yt.title
    except Exception as e:
        import traceback
        print("❌ yt_title error:", e)
        traceback.print_exc()   # <-- this prints full error details
        return None



def download_audio(link):
    try:
        yt = YouTube(link)
        video = yt.streams.filter(only_audio=True).first()
        out_file = video.download(output_path=settings.MEDIA_ROOT)
        base, ext = os.path.splitext(out_file)
        new_file = base + '.mp3'
        os.rename(out_file, new_file)
        return new_file
    except Exception as e:
        print("Download failed:", e)
        return None




def get_transcription(link):
    audio_file = download_audio(link)
    if not audio_file:
        return None
    aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_file)
        return transcript.text
    except Exception as e:
        print("Transcription failed:", e)
        return None

print("DEBUG AssemblyAI Key:", settings.ASSEMBLYAI_API_KEY)



def generate_blog_from_transcription(transcription):
    # use the key from settings, not hardcoded
    openai.api_key = settings.OPENAI_API_KEY
    
    prompt = (
        f"Based on the following transcript from a YouTube video, "
        f"write a comprehensive blog article. Write it based on the transcript, "
        f"but don’t make it sound like a YouTube video—make it look like a proper blog:\n\n"
        f"{transcription}\n\nArticle:"
    )

    response = openai.Completion.create(
  # note: it's Completion, not completions
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=1000
    )

    generated_content = response.choices[0].text.strip()
    return generated_content

    
#def generate_blog_from_transcription(transcription):
    #openai.api_key ='PLACEHOLDER_KEY'
    
    #prompt=f"Based on the following transcript from a youtube video, write a comprehensive blog article, write it based on the transcript,but dont make it sound like a youtube video, make it look like a proper blog:\n\n{transcription}\n\nArticle:"

    #response =openai.completions.create(

       # model="text-davinci-003",
       # prompt=prompt,
       # max_tokens=1000
   # )

    #generated_content=response.choices[0].text.strip()
    #return generated_content

    

def user_login(request):
    if request.method =='POST':
        username= request.POST['username']
        password=request.POST['password']

        user =authenticate (request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect ('/')
        
        else:
            error_message="Invalid username or password"

            return render(request, 'login.html', {'error_message': error_message})

    
    return render(request, 'login.html')

def user_signup(request):
    if request.method =='POST':
        username= request.POST['username']
        password= request.POST['password']
        email= request.POST['email']
        repeatPassword= request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username,email,password)
                user.save()
                login(request,user)
                return redirect('/')
            except:
                error_message ='Error creating account'
                return render (request, 'signup.html', {'error_message' : 'error message'})
            
        else: 
         
         error_message ='Password do not match'   
         return render(request, 'signup.html', {'error_message':error_message})
    return render(request, 'signup.html')


def user_logout(request):
    logout(request)
    return redirect('/')