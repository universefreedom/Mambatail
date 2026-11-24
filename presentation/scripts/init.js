Reveal.initialize({hash:true,controls:true,progress:true,slideNumber:'c/t',center:true,width:1280,height:720,margin:0.06,scrollActivationWidth:null});
const note=document.createElement('aside');note.id='presenter-note';note.hidden=true;note.setAttribute('aria-live','polite');document.body.append(note);
function refreshNote(){const source=document.querySelector('section.present aside.notes');note.textContent=source?.textContent?.trim()||'이 슬라이드에는 별도 발표자 노트가 없습니다.'}
document.addEventListener('keydown',event=>{if(event.key.toLowerCase()==='s'){event.preventDefault();note.hidden=!note.hidden;refreshNote()}});
Reveal.on('slidechanged',refreshNote);Reveal.on('ready',refreshNote);
