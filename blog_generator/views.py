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
import requests
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
import time 
from openai import OpenAI


# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

YT_REGEX = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+')

@csrf_exempt
def generate_blog(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            yt_link = data.get("yt_link")

            # Step 1: Get title
            print("DEBUG yt_link:", yt_link)
            title = yt_title(yt_link)
            if not title:
                return JsonResponse({'error': "Could not fetch YouTube title"}, status=400)

            # Step 2: Get transcription
            transcription = get_transcription(yt_link)
            if not transcription:
                return JsonResponse({'error': "Failed to get transcript"}, status=400)

            # Step 3: Generate blog with title + transcript
            blog_content = generate_blog_from_transcription(title, transcription)

            return JsonResponse({'title': title, 'blog': blog_content}, status=200)

        except Exception as e:
            print("❌ Error in generate_blog:", e)
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': "Invalid request method"}, status=405)
    
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
        audio_stream = yt.streams.filter(only_audio=True).first()
        if not audio_stream:
            print("❌ No audio stream found")
            return None

        # Ensure media folder exists
        media_root = getattr(settings, "MEDIA_ROOT", "media")
        os.makedirs(media_root, exist_ok=True)

        file_path = audio_stream.download(output_path=media_root, filename="yt_audio.mp3")
        print("✅ Audio downloaded to:", file_path)
        return file_path

    except Exception as e:
        print("❌ Audio download failed:", e)
        return None




def get_transcription(link):
    audio_file = download_audio(link)
    if not audio_file:
        print("❌ Failed to download audio")
        return None
    
    return get_transcription_from_file(audio_file)




def get_transcription_from_file(audio_path):
    import assemblyai as aai
    from django.conf import settings

    aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_path)

    if transcript and transcript.text:
        print("✅ Transcript (preview):", transcript.text[:200])  # show first 200 chars
        return transcript.text
    else:
        print("❌ Transcript failed:", transcript.error if transcript else "No response")
        return None
    
    #python manage.py shell

    #from blog_generator.views import get_transcription_from_file
    #get_transcription_from_file("media/test.mp3")
    #in the terminal

from openai import OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_blog_from_transcription(transcription):
    prompt = (
        f"Based on the following transcript from a YouTube video, "
        f"write a comprehensive blog article. Make it engaging, structured, "
        f"and SEO-friendly:\n\n{transcription}\n\nArticle:"
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a professional blog writer."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()

    
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