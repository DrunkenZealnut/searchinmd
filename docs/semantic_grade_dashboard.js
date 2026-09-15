/* Shared occurrence-grade renderer for the NCS and textbook dashboards. */
(function(){
  var D=window.SEMANTIC_RECOUNT, activeCorpus='NCS', activeFilter='all';
  function n(v){return Number(v||0).toLocaleString('ko-KR')}
  function pct(v,d){return d?(v/d*100).toFixed(1):'0.0'}
  function esc(value){return String(value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function corpusData(name){return D.corpora[name]}
  function keywordData(keyword,name){return keyword.corpora[name]}
  function gradedTotal(grades){return grades['1']+grades['2']+grades['3']}
  function gradeRate(grades,grade){return pct(grades[String(grade)],gradedTotal(grades))}
  function corpusLabel(name){return name==='NCS'?'NCS 반도체 교재':'반도체고 교과서'}
  function groupHeading(name){return name==='NCS'?'NCS 영역별 현황':'교과서별 현황'}
  function keywordRows(name,filter){
    var rows=D.keywords.slice().sort(function(a,b){return keywordData(b,name).total-keywordData(a,name).total});
    if(filter==='detected')rows=rows.filter(function(row){return keywordData(row,name).total>0});
    if(filter==='high')rows=rows.slice(0,15);
    return rows.map(function(row){var x=keywordData(row,name),g=x.grades,expressions=row.expressions.length?row.expressions.join(', '):'기존 표현만';return '<tr><td><strong>'+esc(row.name)+'</strong></td><td><strong>'+n(x.total)+'</strong></td><td>'+n(g['1'])+'</td><td>'+n(g['2'])+'</td><td>'+n(g['3'])+'</td><td>'+n(g.unpaged)+'</td><td>'+n(x.exact)+'</td><td>'+n(x.equivalent)+'</td><td>'+n(x.specific)+'</td><td><span class="ts">'+esc(expressions)+'</span></td></tr>'}).join('')
  }
  function groupRows(name){
    return corpusData(name).groups.slice().sort(function(a,b){return b.total-a.total}).map(function(group){var known=gradedTotal(group.grades);return '<tr><td><strong>'+esc(group.name)+'</strong></td><td>'+n(group.documents)+'</td><td><strong>'+n(group.total)+'</strong></td><td>'+n(group.grades['1'])+'</td><td>'+n(group.grades['2'])+'</td><td>'+n(group.grades['3'])+'</td><td>'+n(group.grades.unpaged)+'</td><td>'+pct(group.grades['3'],known)+'%</td></tr>'}).join('')
  }
  function comparisonRows(){
    var a=corpusData('NCS'),b=corpusData('교과서'),ag=gradedTotal(a.grades),bg=gradedTotal(b.grades);
    return '<tr><td><strong>최종 의미 출현</strong></td><td>'+n(a.total)+'건</td><td>'+n(b.total)+'건</td></tr>'+
      '<tr><td><strong>등급 확정 출현</strong></td><td>'+n(ag)+'건</td><td>'+n(bg)+'건</td></tr>'+
      '<tr><td><strong>등급1 — 미흡·없음</strong></td><td>'+n(a.grades['1'])+'건 ('+gradeRate(a.grades,1)+'%)</td><td>'+n(b.grades['1'])+'건 ('+gradeRate(b.grades,1)+'%)</td></tr>'+
      '<tr><td><strong>등급2 — 형식적 언급</strong></td><td>'+n(a.grades['2'])+'건 ('+gradeRate(a.grades,2)+'%)</td><td>'+n(b.grades['2'])+'건 ('+gradeRate(b.grades,2)+'%)</td></tr>'+
      '<tr><td><strong>등급3 — 구체적 대책</strong></td><td>'+n(a.grades['3'])+'건 ('+gradeRate(a.grades,3)+'%)</td><td>'+n(b.grades['3'])+'건 ('+gradeRate(b.grades,3)+'%)</td></tr>'+
      '<tr><td><strong>등급 미확정</strong></td><td>'+n(a.grades.unpaged)+'건</td><td>'+n(b.grades.unpaged)+'건</td></tr>'
  }
  function dataNote(name){
    var run=D.meta.run||{},s=corpusData(name).grade_sources||{};if(!run.xlsx)return '';
    var items=[];                                                     // 등급 출처 — 0건인 출처는 적지 않는다(NCS 는 실제 쪽 판정뿐, 교과서는 승계·신규뿐); 마커 없는 출현만은 0건도 적는다(미배정 없음의 확인)
    if(s['real-page'])items.push('실제 쪽 판정 '+n(s['real-page'])+'건');
    if(s.existing)items.push('기존 판정 승계 '+n(s.existing)+'건');
    if(s['new'])items.push('신규 판정 '+n(s['new'])+'건');
    items.push('마커 없는 출현 문맥 판정 '+n((s['unpaged-context']||0)+(s['unpaged-fallback']||0))+'건');
    return '<br><strong>데이터</strong> — <code>'+esc(run.xlsx)+'</code> (git '+esc(run.git_commit||'?')+(run.git_dirty?'+':'')+', '+esc(String(run.generated_at||'').slice(0,10))+') · '+items.join(' · ')+'.';
  }
  function bridge(name){
    var P=D.meta.previous_basis;if(name!=='NCS'||!P)return '';
    var g=corpusData(name).grades,known=gradedTotal(g),pg=P.page_g,ps=P.pages,unres=P.unresolved_pages;
    var basis=(D.meta.page_basis||{})[name],agree=(D.meta.run||{}).reseg_agreement;
    var realNote='';                                                  // 같은 쪽 기준·같은 규칙이지 같은 쪽 집합은 아니다 — 닿은 쪽 수를 둘 다 적고 차이의 이유를 나눈다 (리뷰 red-team)
    if(basis==='real'){
      var det=corpusData(name).detected_pages;
      var reach=(det!=null?'출현이 놓인 실제 쪽 '+n(det)+'개, ':'')+'이전 기준의 검출 쪽 '+n(P.pages)+'개';
      var agreeNote=agree?', 둘이 공유하는 쪽의 등급 일치 '+n(agree.agree)+'/'+n(agree.pages)+' ('+pct(agree.agree,agree.pages)+'%)':'';
      realNote='<p class="bridge-note" style="margin-bottom:16px;max-width:860px;line-height:1.8">2026-09-15 부터 NCS 출현은 줄→쪽 대응으로 <strong>이전 기준과 같은 실제 PDF 쪽 기준</strong>에 놓이고 그 쪽 본문에 같은 규칙 하나로 판정된다 — '+reach+agreeNote+'. 쪽 집합이 다른 것은 검출 사전(의미 표현 사전 vs 2026-04 문자열 검색)이 다르기 때문이고, 비율이 다른 것은 집계 단위(출현건수 vs 쪽)와 그에 따른 가중(출현이 많은 쪽이 더 무겁다) 때문이다.</p>';
    }
    return '<section style="margin-bottom:48px"><h2>이전 기준(페이지 단위)과의 관계</h2>'+
      '<p class="bridge-note" style="margin-bottom:16px;max-width:860px;line-height:1.8">2026-09-13 부터 공식 KPI 는 <strong>출현건수</strong> 분모다(연구책임자 결정). 그 전까지 발표한 <strong>이전 기준</strong>은 '+esc(P.date||'')+' 재세그먼트의 실제 쪽 단위 — 검출 '+n(P.pages)+'쪽 · 등급3 '+n(pg['3'])+'쪽('+pct(pg['3'],P.pages)+'%) — 이며 <code>'+esc(P.source)+'</code> 에 그대로 남아 있다.</p>'+realNote+
      '<div class="card"><div class="scroll-x" tabindex="0" role="region" aria-label="출현건수 기준과 페이지 기준 브리지 표"><table class="tbl"><thead><tr><th>항목</th><th>출현건수 기준 (공식, 2026-09-13~)</th><th>페이지 기준 (이전 기준, '+esc(P.date||'')+')</th></tr></thead><tbody>'+
      '<tr><td><strong>분자</strong></td><td>등급 g 를 가진 포함 매칭 레코드 수</td><td>등급 g 인 고유 (교재, 실제 쪽) 수</td></tr>'+
      '<tr><td><strong>분모</strong></td><td>등급 확정 출현 '+n(known)+'건 (= 전체 출현, 미확정 '+n(g.unpaged)+')</td><td>키워드 검출 고유 쪽 '+n(P.pages)+'쪽</td></tr>'+
      '<tr><td><strong>같은 쪽의 중복</strong></td><td>매칭마다 1 — 쪽이 키워드 밀도로 가중된다</td><td>쪽당 1</td></tr>'+
      '<tr><td><strong>미확정 처리</strong></td><td>문맥 판정 또는 등급1 배정(미배정 없음)</td><td>마크다운 없는 교재는 라벨 유지'+(unres?' ('+n(unres)+'쪽)':'')+'</td></tr>'+
      '<tr><td><strong>코퍼스</strong></td><td>'+n(corpusData(name).documents)+'권 마크다운</td><td>'+n(P.books)+'권 (마크다운 + 라벨 유지 교재)</td></tr>'+
      '<tr><td><strong>읽는 법</strong></td><td>키워드가 나오는 자리 중 몇 %가 구체적 대책 페이지에 있는가</td><td>검출된 쪽 중 몇 %가 구체적 대책인가</td></tr>'+
      '<tr><td><strong>등급1 비율</strong></td><td>'+n(g['1'])+'건 ('+gradeRate(g,1)+'%)</td><td>'+n(pg['1'])+'쪽 ('+pct(pg['1'],ps)+'%)</td></tr>'+
      '<tr><td><strong>등급2 비율</strong></td><td>'+n(g['2'])+'건 ('+gradeRate(g,2)+'%)</td><td>'+n(pg['2'])+'쪽 ('+pct(pg['2'],ps)+'%)</td></tr>'+
      '<tr><td><strong>등급3 비율</strong></td><td>'+n(g['3'])+'건 ('+gradeRate(g,3)+'%)</td><td>'+n(pg['3'])+'쪽 ('+pct(pg['3'],ps)+'%)</td></tr>'+
      '</tbody></table></div></div>'+
      '<p class="bridge-note" style="margin-top:12px;max-width:860px;line-height:1.8"><strong>두 값의 차이는 가중 방식의 차이이지 교재가 나아졌거나 측정이 정밀해진 것이 아니다.</strong> 등급3 페이지는 정의상 안전어·조치어가 많은 쪽이라 출현 가중에서는 그 몫이 페이지 비중의 약 3배로 보인다. 출현 비율을 페이지 비율의 개선으로 읽지 말 것.</p></section>';
  }
  function insights(name){
    var c=corpusData(name),g=c.grades,known=gradedTotal(g),top=D.keywords.slice().sort(function(a,b){return keywordData(b,name).total-keywordData(a,name).total}).slice(0,3),topTotal=top.reduce(function(sum,row){return sum+keywordData(row,name).total},0);
    var fourth=name==='NCS'
      ? '<div class="ins"><h3>4. 페이지 기준 수치와 나란히 읽기</h3><p>출현건수 비율은 키워드가 많은 쪽을 그만큼 무겁게 센 값입니다. '+(D.meta.previous_basis?'페이지 단위 이전 기준(등급3 '+pct(D.meta.previous_basis.page_g['3'],D.meta.previous_basis.pages)+'%)과의 차이는 아래 "이전 기준과의 관계" 절의 브리지 표를 보십시오. ':'')+'마커 없는 출현 '+n(((c.grade_sources||{})['unpaged-context']||0)+((c.grade_sources||{})['unpaged-fallback']||0))+'건은 문맥으로 판정해 미배정을 두지 않았습니다.</p></div>'
      : '<div class="ins"><h3>4. 낮은 빈도 키워드도 별도 검토 필요</h3><p>출현건수가 적거나 0인 키워드는 교육 내용의 실제 누락인지 원문 문맥과 함께 확인해야 합니다.</p></div>';
    return '<div class="ins"><h3>1. 등급1 출현 비중</h3><p>등급이 확정된 의미 출현 중 <strong>'+n(g['1'])+'건('+gradeRate(g,1)+'%)</strong>이 미흡·없음으로 분류됐습니다.</p></div>'+
      '<div class="ins"><h3>2. 구체적 대책 출현</h3><p>등급3은 <strong>'+n(g['3'])+'건('+gradeRate(g,3)+'%)</strong>입니다. 출현 빈도와 실제 교육 내용의 충실도는 함께 확인해야 합니다.</p></div>'+
      '<div class="ins"><h3>3. 상위 키워드 집중</h3><p><strong>'+top.map(function(row){return esc(row.name)}).join('·')+'</strong> 세 키워드가 '+n(topTotal)+'건으로 전체의 '+pct(topTotal,c.total)+'%를 차지합니다.</p></div>'+fourth
  }
  function render(name){
    activeCorpus=name==='교과서'?'교과서':'NCS';activeFilter='all';var c=corpusData(activeCorpus),g=c.grades,known=gradedTotal(g),title=corpusLabel(activeCorpus),unpagedNote=g.unpaged?' · 등급 미확정 '+n(g.unpaged)+'건':' · 모든 출현 등급 확정';
    document.querySelector('.ctn').innerHTML=
      '<section class="hero"><h1>'+title.replace(' ','<br>')+'<br>안전보건 키워드 분석</h1><p>30개 독립 키워드의 정확·동등·구체 표현을 문맥 검토해 의미 출현마다 페이지 등급을 결합한 결과</p><div class="hs-row"><div class="hs"><div class="hs-v">'+n(c.total)+'</div><div class="hs-l">최종 의미 출현</div></div><div class="hs"><div class="hs-v">'+n(known)+'</div><div class="hs-l">등급 확정 출현</div></div><div class="hs"><div class="hs-v">30</div><div class="hs-l">독립 키워드</div></div><div class="hs"><div class="hs-v">'+n(c.documents)+'</div><div class="hs-l">분석 문서</div></div></div><p class="ts" style="margin-top:24px;max-width:860px;margin-left:auto;margin-right:auto;text-align:left;line-height:1.9"><strong>등급 체계</strong> — 등급1: 미흡·없음 / 등급2: 형식적 언급 / 등급3: 구체적 대책.<br><strong>분류 기준</strong> — 비율과 차트는 페이지 수가 아니라 문맥이 확인된 <strong>출현건수</strong>를 분모로 합니다'+unpagedNote+'. 총계는 키워드-표현 매칭 레코드 합계이지 고유 문장·쪽 수가 아닙니다.'+dataNote(activeCorpus)+'</p></section>'+
      '<section class="g4"><div class="card kpi"><div class="kpi-v" style="color:var(--g1)">'+n(g['1'])+'</div><div class="kpi-l">등급1 — 미흡·없음</div><div class="kpi-bar"><i style="width:'+gradeRate(g,1)+'%;background:var(--g1)"></i></div><div class="ts" style="margin-top:8px">등급 확정 출현의 '+gradeRate(g,1)+'%</div></div><div class="card kpi"><div class="kpi-v" style="color:var(--g2)">'+n(g['2'])+'</div><div class="kpi-l">등급2 — 형식적 언급</div><div class="kpi-bar"><i style="width:'+gradeRate(g,2)+'%;background:var(--g2)"></i></div><div class="ts" style="margin-top:8px">등급 확정 출현의 '+gradeRate(g,2)+'%</div></div><div class="card kpi"><div class="kpi-v" style="color:var(--g3)">'+n(g['3'])+'</div><div class="kpi-l">등급3 — 구체적 대책</div><div class="kpi-bar"><i style="width:'+gradeRate(g,3)+'%;background:var(--g3)"></i></div><div class="ts" style="margin-top:8px">등급 확정 출현의 '+gradeRate(g,3)+'%</div></div><div class="card kpi"><div class="kpi-v" style="color:var(--text-secondary)">'+n(g.unpaged)+'</div><div class="kpi-l">등급 미확정</div><div class="kpi-bar"><i style="width:'+pct(g.unpaged,c.total)+'%;background:var(--text-secondary)"></i></div><div class="ts" style="margin-top:8px">전체 출현의 '+pct(g.unpaged,c.total)+'%</div></div></section>'+
      bridge(activeCorpus)+
      '<section><h2>전체 등급 분포</h2><div class="g2"><div class="card"><h3 style="margin-bottom:4px">등급별 의미 출현</h3><p class="ts" style="margin-bottom:8px">등급 확정 출현건수 기준</p><div class="cc"><canvas id="gradeC1"></canvas></div></div><div class="card"><h3 style="margin-bottom:4px">상위 키워드별 등급 분포</h3><p class="ts" style="margin-bottom:8px">단위: 의미 출현건수</p><div class="cc"><canvas id="gradeC2"></canvas></div></div></div></section>'+
      '<section style="margin-bottom:48px"><h2>키워드별 상세</h2><div class="fb"><button type="button" class="fbtn on" aria-pressed="true" onclick="semanticGradeFilter(\'all\',this)">전체</button><button type="button" class="fbtn" aria-pressed="false" onclick="semanticGradeFilter(\'detected\',this)">검출 키워드</button><button type="button" class="fbtn" aria-pressed="false" onclick="semanticGradeFilter(\'high\',this)">상위15</button></div><div class="card"><div class="scroll-x" tabindex="0" role="region" aria-label="키워드별 등급 출현 표"><table class="tbl"><thead><tr><th>키워드</th><th>최종 출현</th><th>등급1</th><th>등급2</th><th>등급3</th><th>미확정</th><th>유효 정확</th><th>동등 추가</th><th>구체 추가</th><th>포함 확장 표현</th></tr></thead><tbody id="gradeKeywordBody">'+keywordRows(activeCorpus,'all')+'</tbody></table></div></div><p class="ts" style="margin-top:12px">* 등급 열은 해당 등급 페이지에 속한 표현의 출현건수입니다. 같은 페이지의 여러 출현은 각각 집계합니다.</p></section>'+
      '<section style="margin-bottom:48px"><h2>'+groupHeading(activeCorpus)+'</h2><div class="card"><div class="scroll-x" tabindex="0" role="region" aria-label="'+groupHeading(activeCorpus)+' 표"><table class="tbl"><thead><tr><th>'+(activeCorpus==='NCS'?'영역':'교과서')+'</th><th>문서</th><th>최종 출현</th><th>등급1</th><th>등급2</th><th>등급3</th><th>미확정</th><th>등급3 비율</th></tr></thead><tbody>'+groupRows(activeCorpus)+'</tbody></table></div></div></section>'+
      '<section style="margin-bottom:48px"><h2>문제점과 시사점</h2>'+insights(activeCorpus)+'</section>'+
      '<section style="margin-bottom:48px"><h2>NCS 교재 vs 교과서 비교</h2><p class="ts" style="margin-bottom:16px">같은 30개 키워드와 같은 통일 등급을 사용하며, 모든 비율은 등급이 확정된 출현건수를 분모로 합니다.</p><div class="card"><div class="scroll-x" tabindex="0" role="region" aria-label="NCS와 교과서 등급 출현 비교 표"><table class="tbl"><thead><tr><th>항목</th><th>NCS 교재</th><th>교과서</th></tr></thead><tbody>'+comparisonRows()+'</tbody></table></div></div></section>'+
      '<section style="margin-bottom:48px"><h2>개선 권고안</h2><div class="rec"><h3>1. 등급1이 많은 키워드의 문맥 보강</h3><p>단순 반복보다 공정별 위험요인, 예방조치, 보호구, 응급대응을 실제 작업 문맥으로 제시해야 합니다.</p></div><div class="rec"><h3>2. 등급3 출현의 내용 품질 확인</h3><p>출현건수는 빈도 지표입니다. 실제 조치가 실행 가능한 절차인지 원문을 함께 검토해야 합니다.</p></div><div class="rec"><h3>3. 같은 분모로 계속 비교</h3><p>NCS와 교과서의 후속 분석도 페이지 비율과 출현 비율을 섞지 말고 의미 출현건수 기준을 유지해야 합니다.</p></div></section>'+
      '<footer style="text-align:center;padding:32px 0;color:var(--text-secondary);font-size:var(--fs-sm)">'+title+' 안전보건 분석 | 등급1~3 출현건수 기준 | 2026년</footer>';
    charts();
  }
  function charts(){
    if(typeof Chart==='undefined')return;var c=corpusData(activeCorpus),g=c.grades,top=D.keywords.slice().sort(function(a,b){return keywordData(b,activeCorpus).total-keywordData(a,activeCorpus).total}).slice(0,10),style=getComputedStyle(document.documentElement),color=function(name){return style.getPropertyValue(name).trim()};
    ['gradeC1','gradeC2'].forEach(function(id){var old=Chart.getChart&&Chart.getChart(id);if(old&&old.destroy)old.destroy()});
    var one=document.getElementById('gradeC1'),two=document.getElementById('gradeC2');if(!one||!two)return;
    new Chart(one,{type:'doughnut',data:{labels:['등급1 미흡·없음','등급2 형식적 언급','등급3 구체적 대책'],datasets:[{data:[g['1'],g['2'],g['3']],backgroundColor:[color('--g1'),color('--g2'),color('--g3')],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,cutout:'60%',plugins:{legend:{position:'bottom',labels:{color:color('--text'),padding:14}}}}});
    new Chart(two,{type:'bar',data:{labels:top.map(function(row){return row.name}),datasets:[{label:'등급1 미흡·없음',data:top.map(function(row){return keywordData(row,activeCorpus).grades['1']}),backgroundColor:color('--g1')},{label:'등급2 형식적 언급',data:top.map(function(row){return keywordData(row,activeCorpus).grades['2']}),backgroundColor:color('--g2')},{label:'등급3 구체적 대책',data:top.map(function(row){return keywordData(row,activeCorpus).grades['3']}),backgroundColor:color('--g3')}]},options:{responsive:true,maintainAspectRatio:false,indexAxis:'y',scales:{x:{stacked:true,ticks:{color:color('--text-secondary')},grid:{color:color('--border')}},y:{stacked:true,ticks:{color:color('--text')},grid:{display:false}}},plugins:{legend:{position:'top',labels:{color:color('--text'),padding:12}}}}});
  }
  window.semanticGradeFilter=function(filter,button){activeFilter=filter;document.querySelectorAll('.fb .fbtn').forEach(function(item){item.classList.remove('on');item.setAttribute('aria-pressed','false')});if(button){button.classList.add('on');button.setAttribute('aria-pressed','true')}var body=document.getElementById('gradeKeywordBody');if(body)body.innerHTML=keywordRows(activeCorpus,activeFilter)};
  window.renderSemanticGradeDashboard=render;
  window.onThemeChange=charts;
  window.buildCharts=charts;
  window.rKT=function(){};
  window.updSortIndicators=function(){};
  if(window.SEMANTIC_DASHBOARD_CORPUS)render(window.SEMANTIC_DASHBOARD_CORPUS);
})();
