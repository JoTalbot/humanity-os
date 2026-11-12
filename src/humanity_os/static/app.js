(() => {
"use strict";
let csrfToken = null;
let statusTimeout = null;
const $ = (selector) => document.querySelector(selector);
const loginView = $("#login-view");
const workspaceView = $("#workspace-view");
const logoutButton = $("#logout-button");
const statusBox = $("#status-message");
function notify(message,isError=false){statusBox.textContent=message;statusBox.dataset.error=String(isError);statusBox.classList.add("visible");window.clearTimeout(statusTimeout);statusTimeout=window.setTimeout(()=>statusBox.classList.remove("visible"),4200);}
async function api(path,options={}){
 const method=(options.method||"GET").toUpperCase();const headers=new Headers(options.headers||{});
 if(options.body!==undefined)headers.set("Content-Type","application/json");
 if(!["GET","HEAD","OPTIONS"].includes(method)&&csrfToken)headers.set("X-CSRF-Token",csrfToken);
 const response=await fetch(path,{...options,method,headers,credentials:"same-origin",cache:"no-store"});
 const raw=await response.text();let data=null;try{data=raw?JSON.parse(raw):null;}catch{data=raw;}
 if(!response.ok){const detail=data&&typeof data==="object"?data.detail:null;throw new Error(detail||"Request failed ("+response.status+")");}
 return data;
}
function setSignedIn(signedIn){loginView.classList.toggle("hidden",signedIn);workspaceView.classList.toggle("hidden",!signedIn);logoutButton.classList.toggle("hidden",!signedIn);$("#connection-state").textContent=signedIn?"Session active · local":"Local workspace";}
function element(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
function itemCard(title,copy,meta){const card=element("article","item");card.append(element("h4","item-title",title||"Untitled"));if(copy)card.append(element("p","item-copy",copy));if(meta)card.append(element("div","item-meta",meta));return card;}
function actionButton(label,action,danger=false){const button=element("button","button "+(danger?"button-danger":"button-secondary"),label);button.type="button";button.addEventListener("click",action);return button;}
function renderList(target,items,emptyText,renderer){target.replaceChildren();if(!items.length){target.classList.add("empty-state");target.textContent=emptyText;return;}target.classList.remove("empty-state");for(const item of items)target.append(renderer(item));}
async function loadNotes(){const query=$("#note-search").value.trim();const path=query?"/v1/knowledge?limit=30&q="+encodeURIComponent(query):"/v1/knowledge?limit=30";const result=await api(path);const items=result.items||[];$("#note-count").textContent=String(items.length);renderList($("#notes-list"),items,"No matching notes.",note=>itemCard(note.title,note.content,note.kind+" · "+note.visibility+" · "+note.id));renderList($("#overview-notes"),items.slice(0,4),"No notes yet.",note=>itemCard(note.title,note.content.slice(0,160),note.kind+" · "+note.id));}
async function loadDocuments(){const result=await api("/v1/documents?limit=50");const items=result.items||[];$("#document-count").textContent=String(items.length);renderList($("#documents-list"),items,"No documents yet.",doc=>itemCard(doc.filename,doc.character_count+" characters · "+doc.chunk_count+" chunks",doc.media_type+" · SHA-256 "+doc.content_hash));}
async function loadModelCapabilities(){
 const capabilities=await api("/v1/models/capabilities");
 const configured=capabilities.provider_configured;
 $("#answer-submit").disabled=!configured;
 $("#provider-status").textContent=configured
  ?"Configured provider: "+capabilities.provider_id+" / "+capabilities.model_id+". Source passages are sent only after your per-request approval."
  :"No model provider is configured. Local source context remains available; answer generation is disabled.";
}
async function loadMemory(){
 const values=await Promise.all([api("/v1/memory/proposals?status=pending_review&limit=50"),api("/v1/memories?limit=100"),api("/v1/memory/events")]);
 const proposals=values[0].items||[];const memories=values[1].items||[];const events=values[2].items||[];$("#proposal-count").textContent=String(proposals.length);
 renderList($("#overview-memory"),proposals.slice(0,3),"No pending proposals.",p=>itemCard(p.title,p.content.slice(0,140),"Pending review · "+p.id));
 renderList($("#proposals-list"),proposals,"No pending proposals.",proposal=>{
  const card=itemCard(proposal.title,proposal.content,proposal.rationale);
  if(proposal.source_document_id)card.append(element("div","item-meta","Source: "+proposal.source_document_id+" · chunk "+proposal.source_chunk_id));
  const actions=element("div","item-actions");
  actions.append(actionButton("Approve memory",async()=>{try{await api("/v1/memory/proposals/"+encodeURIComponent(proposal.id)+"/approve",{method:"POST"});notify("Memory approved.");await loadMemory();}catch(error){notify(error.message,true);}}));
  actions.append(actionButton("Reject",async()=>{try{await api("/v1/memory/proposals/"+encodeURIComponent(proposal.id)+"/reject",{method:"POST"});notify("Proposal rejected.");await loadMemory();}catch(error){notify(error.message,true);}},true));
  card.append(actions);return card;
 });
 renderList($("#memories-list"),memories,"No approved memories yet.",memory=>{
  const card=itemCard(memory.title,memory.content,memory.status+" · "+memory.content_hash);const actions=element("div","item-actions");const archived=memory.status==="archived";
  actions.append(actionButton(archived?"Restore":"Archive",async()=>{try{await api("/v1/memories/"+encodeURIComponent(memory.id)+"/"+(archived?"restore":"archive"),{method:"POST"});notify(archived?"Memory restored.":"Memory archived.");await loadMemory();}catch(error){notify(error.message,true);}}));
  card.append(actions);return card;
 });
 renderList($("#memory-events"),events,"No memory events yet.",event=>itemCard(event.event_type.replaceAll("_"," "),event.details,event.actor+" · "+event.occurred_at));
}
async function refreshAll(){try{await Promise.all([loadNotes(),loadDocuments(),loadMemory(),loadModelCapabilities()]);}catch(error){if(/Authentication required/i.test(error.message)){csrfToken=null;setSignedIn(false);}notify(error.message,true);}}
$("#login-form").addEventListener("submit",async event=>{event.preventDefault();try{const result=await api("/auth/login",{method:"POST",body:JSON.stringify({password:$("#password").value})});csrfToken=result.csrf_token;$("#password").value="";setSignedIn(true);await refreshAll();notify("Workspace unlocked.");}catch(error){notify(error.message,true);}});
logoutButton.addEventListener("click",async()=>{try{await api("/auth/logout",{method:"POST"});csrfToken=null;setSignedIn(false);notify("Signed out.");}catch(error){notify(error.message,true);}});
$("#note-form").addEventListener("submit",async event=>{event.preventDefault();try{await api("/v1/knowledge",{method:"POST",body:JSON.stringify({kind:"observation",title:$("#note-title").value,content:$("#note-content").value,visibility:"private"})});$("#note-form").reset();notify("Note saved.");await loadNotes();}catch(error){notify(error.message,true);}});
$("#note-search").addEventListener("input",()=>{window.clearTimeout(statusTimeout);statusTimeout=window.setTimeout(()=>loadNotes().catch(error=>notify(error.message,true)),220);});
$("#refresh-notes").addEventListener("click",()=>loadNotes().catch(error=>notify(error.message,true)));
$("#document-form").addEventListener("submit",async event=>{event.preventDefault();try{await api("/v1/documents",{method:"POST",body:JSON.stringify({filename:$("#document-filename").value,content:$("#document-content").value})});$("#document-form").reset();notify("Document added locally.");await loadDocuments();}catch(error){notify(error.message,true);}});
$("#document-search-form").addEventListener("submit",async event=>{event.preventDefault();try{const result=await api("/v1/documents/search",{method:"POST",body:JSON.stringify({query:$("#document-query").value,limit:20})});renderList($("#document-results"),result.items||[],"No matching source chunks.",match=>itemCard(match.filename,match.excerpt,"Document "+match.document_id+" · chunk "+match.chunk_id+" · chars "+match.start_offset+"-"+match.end_offset));}catch(error){notify(error.message,true);}});
$("#memory-proposal-form").addEventListener("submit",async event=>{event.preventDefault();try{await api("/v1/memory/proposals",{method:"POST",body:JSON.stringify({title:$("#memory-title").value,content:$("#memory-content").value,rationale:$("#memory-rationale").value})});$("#memory-proposal-form").reset();notify("Proposal submitted. Approval is still required.");await loadMemory();}catch(error){notify(error.message,true);}});
$("#prepare-context").addEventListener("click",async()=>{const query=$("#document-query").value.trim();if(!query){notify("Enter a search query first.",true);return;}try{const result=await api("/v1/documents/context",{method:"POST",body:JSON.stringify({query:query,passage_limit:5,max_context_chars:8000})});const card=itemCard("Prepared source context",result.context,"Local lexical retrieval · model called: "+result.processing.model_called+" · external processing: "+result.processing.external_processing);for(const source of result.passages){card.append(element("div","item-meta","["+source.citation_id+"] "+source.filename+" · document "+source.document_id+" · chunk "+source.chunk_id+" · chars "+source.start_offset+"-"+source.end_offset+(source.truncated?" · excerpt truncated":"")));}renderList($("#context-results"),[card],"No matching source context.",item=>item);notify("Source context prepared locally.");}catch(error){notify(error.message,true);}});
$("#answer-form").addEventListener("submit",async event=>{
 event.preventDefault();
 if(!$("#provider-consent").checked){notify("Explicit provider consent is required.",true);return;}
 const query=$("#document-query").value.trim();
 if(!query){notify("Enter a source search query first.",true);return;}
 try{
  const result=await api("/v1/documents/answer",{method:"POST",body:JSON.stringify({query:query,allow_provider_processing:true,passage_limit:5,max_context_chars:8000,max_output_tokens:768})});
  const card=itemCard("Grounded answer",result.answer,"Provider "+result.provider+" · model "+result.model+" · semantic entailment independently verified: "+result.processing.semantic_entailment_verified);
  for(const source of result.citations)card.append(element("div","item-meta","["+source.citation_id+"] "+source.filename+" · document "+source.document_id+" · chunk "+source.chunk_id+" · chars "+source.start_offset+"-"+source.end_offset));
  renderList($("#answer-results"),[card],"No grounded answer returned.",item=>item);
  $("#provider-consent").checked=false;
  notify("Answer generated. Review its source citations.");
 }catch(error){notify(error.message,true);}
});
$("#refresh-documents").addEventListener("click",()=>loadDocuments().catch(error=>notify(error.message,true)));
$("#refresh-memory").addEventListener("click",()=>loadMemory().catch(error=>notify(error.message,true)));
document.querySelectorAll("[data-tab],[data-open-tab]").forEach(button=>button.addEventListener("click",()=>{const tab=button.dataset.tab||button.dataset.openTab;document.querySelectorAll(".tab").forEach(item=>{const active=item.dataset.tab===tab;item.classList.toggle("active",active);if(active)item.setAttribute("aria-current","page");else item.removeAttribute("aria-current");});document.querySelectorAll(".tab-panel").forEach(panel=>panel.classList.toggle("hidden",panel.id!=="tab-"+tab));if(tab==="memory")loadMemory().catch(error=>notify(error.message,true));if(tab==="documents")loadDocuments().catch(error=>notify(error.message,true));if(tab==="notes")loadNotes().catch(error=>notify(error.message,true));}));
setSignedIn(false);
})();
