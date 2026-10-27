// agents_init.js — Starts the agents UI and adds the voice buttons. Loads last: it calls
// functions from agents.js, agent_builder.js, agent_run.js and agent_builder_chat.js.

document.addEventListener('keydown',function(e){
  const inp=document.getElementById('builder-chat-inp');
  if(!inp||document.activeElement!==inp) return;
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendBuilderChat();}
});

// ---------------------------------------------------------------------------
(function _agentsInit(){
  function _exposeAgentGlobals(){
    window.loadAgentsPanel=loadAgentsPanel;
    window.openAgentBuilder=openAgentBuilder;
    window.openAgentBuilderWindow=openAgentBuilderWindow;
    window.closeAgentBuilder=closeAgentBuilder;
    window.closeAgentRunOverlay=closeAgentRunOverlay;
    window._importAgentFromFile=_importAgentFromFile;
    window._openMonitorDashboard=_openMonitorDashboard;
  }

  function _bindAgentSidebarButtons(){
    const bind=(id,handler)=>{
      const btn=document.getElementById(id);
      if(!btn||btn.dataset.agentBound) return;
      btn.dataset.agentBound='1';
      btn.addEventListener('click',e=>{
        e.preventDefault();
        e.stopPropagation();
        handler();
      });
    };
    bind('agent-new-btn',()=>openAgentBuilder(null));
    bind('agent-import-btn',()=>_importAgentFromFile());
    bind('agent-monitor-btn',()=>_openMonitorDashboard());
  }

  function _maybeOpenBuilderFromUrl(){
    const qs=new URLSearchParams(window.location.search||'');
    const mode=qs.get('agent_builder');
    if(!mode||window.__agentBuilderUrlOpened) return;
    window.__agentBuilderUrlOpened=true;
    if(mode==='edit'){
      const agentId=qs.get('agent_id');
      if(!agentId) return;
      fetch('/api/agents/'+encodeURIComponent(agentId)).then(r=>r.json()).then(data=>{
        if(data.agent){
          _agents[data.agent.id]=data.agent;
          openAgentBuilder(data.agent.id);
        }
      }).catch(()=>{});
      return;
    }
    openAgentBuilder(null);
  }

  function _hookAgentsSection(){
    const section=document.querySelector('[data-section="agents"]');
    if(!section) return;
    const obs=new MutationObserver(()=>{
      if(section.classList.contains('open')&&!section.dataset.agLoaded){
        section.dataset.agLoaded='1';loadAgentsPanel();
      }
    });
    obs.observe(section,{attributes:true});
    if(section.classList.contains('open')) loadAgentsPanel();
  }
  _exposeAgentGlobals();
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',()=>{_bindAgentSidebarButtons();_hookAgentsSection();_maybeOpenBuilderFromUrl();_initAgentMicButtons();});
  }else{
    _bindAgentSidebarButtons();
    _hookAgentsSection();
    _maybeOpenBuilderFromUrl();
    _initAgentMicButtons();
  }

  // Fix canvas background on builder open
  const origOpen=window.openAgentBuilder;
  // Patch after DOM ready so the overlay elements exist
  document.addEventListener('DOMContentLoaded',()=>{
    const overlay=document.getElementById('agent-builder-overlay');
    if(overlay){
      const obs2=new MutationObserver(()=>{
        if(overlay.style.display!=='none'){_fixCanvasBg();_initAgentMicButtons();}
      });
      obs2.observe(overlay,{attributes:true,attributeFilter:['style']});
    }
  });

  // -------------------------------------------------------------------------
  // Voice input for agent builder fields (description, generate modal, chat).
  // Each mic button gets its own MediaRecorder + state so they cannot collide.
  // -------------------------------------------------------------------------
  function _initAgentMicButtons(){
    _attachAgentMic('agent-desc-inp',  {position:'inline'});
    _attachAgentMic('agent-gen-desc',  {position:'corner'});
    _attachAgentMic('builder-chat-inp',{position:'corner'});
    _attachAgentMic('node-task-inp',   {position:'corner'});
  }

  function _buildMicSvg(){
    // Filled capsule mic — recognizable at small sizes. Body solid, stand stroked.
    const SVG_NS='http://www.w3.org/2000/svg';
    const svg=document.createElementNS(SVG_NS,'svg');
    svg.setAttribute('width','26');
    svg.setAttribute('height','26');
    svg.setAttribute('viewBox','0 0 24 24');
    svg.setAttribute('aria-hidden','true');
    // Solid mic capsule (head)
    const capsule=document.createElementNS(SVG_NS,'rect');
    capsule.setAttribute('x','9');
    capsule.setAttribute('y','2');
    capsule.setAttribute('width','6');
    capsule.setAttribute('height','12');
    capsule.setAttribute('rx','3');
    capsule.setAttribute('fill','currentColor');
    svg.appendChild(capsule);
    // Stand + base, stroked
    const stand=document.createElementNS(SVG_NS,'path');
    stand.setAttribute('d','M5 11v1a7 7 0 0 0 14 0v-1 M12 19v3 M8 22h8');
    stand.setAttribute('stroke','currentColor');
    stand.setAttribute('stroke-width','2.5');
    stand.setAttribute('stroke-linecap','round');
    stand.setAttribute('stroke-linejoin','round');
    stand.setAttribute('fill','none');
    svg.appendChild(stand);
    return svg;
  }

  function _attachAgentMic(targetId, opts){
    const target=document.getElementById(targetId);
    if(!target || target.dataset.micAttached==='1') return;
    target.dataset.micAttached='1';

    const btn=document.createElement('button');
    btn.type='button';
    // Visual state lives entirely in overhaul.css under `.agent-mic-btn`;
    // we only set positioning/sizing here.
    btn.className='agent-mic-btn';
    btn.setAttribute('aria-label','Voice input for '+targetId);
    btn.title='Click to record voice — Whisper will transcribe into this field';
    btn.appendChild(_buildMicSvg());

    if(opts && opts.position==='inline'){
      btn.style.cssText='width:44px;height:44px;border-radius:11px;flex-shrink:0;margin-left:6px';
      if(target.parentElement) target.parentElement.insertBefore(btn,target.nextSibling);
    } else {
      const parent=target.parentElement;
      if(parent && getComputedStyle(parent).position==='static') parent.style.position='relative';
      btn.style.cssText='position:absolute;right:10px;bottom:10px;width:44px;height:44px;border-radius:11px;z-index:5';
      if(parent) parent.appendChild(btn);
    }

    let mediaRec=null, chunks=[], recording=false;
    btn.addEventListener('click', async ()=>{
      if(recording){
        if(mediaRec && mediaRec.state!=='inactive') mediaRec.stop();
        return;
      }
      try {
        const stream=await navigator.mediaDevices.getUserMedia({audio:true});
        const mime=_pickSupportedMime();
        mediaRec=new MediaRecorder(stream, mime?{mimeType:mime}:undefined);
        chunks=[];
        mediaRec.ondataavailable=e=>{ if(e.data && e.data.size>0) chunks.push(e.data); };
        mediaRec.onstop=async()=>{
          stream.getTracks().forEach(t=>t.stop());
          recording=false;
          btn.classList.remove('recording');
          btn.title='Click to record voice — Whisper will transcribe into this field';
          if(chunks.length===0) return;
          const blob=new Blob(chunks,{type:mediaRec.mimeType||'audio/webm'});
          await _transcribeIntoField(blob, target, btn);
        };
        mediaRec.start();
        recording=true;
        btn.classList.add('recording');
        btn.title='Click to stop recording';
      } catch(err) {
        console.error('Mic access denied:',err);
        alert('Microphone access denied. Allow microphone in browser settings.');
      }
    });
  }

  function _pickSupportedMime(){
    if(typeof MediaRecorder==='undefined') return '';
    const types=['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/mp4'];
    for(const t of types){ if(MediaRecorder.isTypeSupported(t)) return t; }
    return '';
  }

  async function _transcribeIntoField(blob, target, btn){
    btn.disabled=true;  // CSS [disabled] handles the wait styling
    try {
      const form=new FormData();
      form.append('file',blob,'recording.webm');
      const headers={};
      if(typeof _csrfToken==='function') headers['x-csrf-token']=_csrfToken();
      const resp=await fetch('/transcribe',{method:'POST',headers,body:form});
      const data=await resp.json();
      if(data.error){ alert('Transcription failed: '+data.error); return; }
      if(data.text){
        const sep=target.value && !target.value.endsWith(' ')?' ':'';
        target.value=(target.value||'')+sep+data.text;
        target.focus();
        try{ target.dispatchEvent(new Event('input',{bubbles:true})); }catch(_){ }
      }
    } catch(err) {
      console.error('Transcription request failed:',err);
      alert('Could not reach transcription server.');
    } finally {
      btn.disabled=false;
      btn.title='Click to record voice — Whisper will transcribe into this field';
    }
  }
})();
