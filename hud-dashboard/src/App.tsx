import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export default function App() {
  const [time, setTime] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(timer);
  }, []);

  const barData = [
    { name: 'r1', value: 65, color: '#00ffff' },
    { name: 'r2', value: 74, color: '#ff0000' },
    { name: 'r3', value: 80, color: '#00ffff' },
    { name: 'r4', value: 91, color: '#00ffff' },
    { name: 'r5', value: 75, color: '#00ffff' },
    { name: 'r6', value: 83, color: '#00ffff' },
    { name: 'r7', value: 72, color: '#00ffff' },
    { name: 'r8', value: 74, color: '#ff0000' },
    { name: 'r9', value: 45, color: '#00ffff' },
    { name: 'r10', value: 33, color: '#00ffff' },
    { name: 'r11', value: 78, color: '#00ffff' },
    { name: 'r12', value: 53, color: '#00ffff' },
  ];

  return (
    <div className="w-screen h-screen bg-black text-white font-mono overflow-hidden flex flex-col p-6 dot-grid text-xs select-none">
      <div className="w-full max-w-[1600px] h-full mx-auto grid grid-cols-12 gap-8 relative z-10">
        
        {/* LEFT COLUMN (approx 3 cols) */}
        <div className="col-span-3 flex flex-col h-full gap-4 pt-2">
          
          {/* HUD Title */}
          <div className="mb-4">
            <div className="flex items-end gap-2">
              <h1 className="text-4xl font-bold text-[#00ffff] tracking-widest leading-none">HUD</h1>
              <span className="text-red-500 text-sm mb-1 tracking-widest font-semibold">ONLINE</span>
            </div>
            <div className="text-[10px] text-[#00ffff] tracking-[0.3em] mt-2 flex justify-between">
              <span>A N A L Y Z I N G</span>
              <span>{time}</span>
            </div>
          </div>
          
          {/* Waveforms & Data */}
          <div className="flex-1 flex flex-col pt-4">
            <div className="h-16 w-full flex items-center justify-center gap-1 opacity-60 mb-6">
              {Array.from({length: 40}).map((_, i) => (
                <div key={i} className="w-[2px] bg-[#00ffff]" style={{height: `${Math.random() * 100}%`}}></div>
              ))}
            </div>

            {/* Horizontal Bar Chart */}
            <div className="flex-1 w-full relative pl-8 border-l border-red-600/50">
              <div className="flex flex-col justify-between h-full py-2">
                {barData.map((d, i) => (
                  <div key={i} className="flex items-center gap-2 group">
                    <span className="absolute left-0 -ml-6 text-[9px] text-[#00ffff]/60">{d.name}</span>
                    <div className="flex-1 h-3 bg-black border border-white/10 relative">
                       <motion.div 
                          className="h-full" 
                          style={{ backgroundColor: d.color, width: `${d.value}%` }}
                          initial={{ width: 0 }}
                          animate={{ width: `${d.value}%` }}
                          transition={{ duration: 1, delay: i * 0.05 }}
                       />
                    </div>
                    <span className="w-6 text-right font-bold text-sm" style={{ color: d.color }}>{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* MIDDLE COLUMN (approx 4 cols) */}
        <div className="col-span-4 flex flex-col h-full gap-6">
           
           {/* Calendar Header */}
           <div className="flex justify-between items-start border-t border-[#00ffff]/30 pt-2 relative mt-4">
              <div className="absolute -top-1 -left-1 w-2 h-2 bg-red-600"></div>
              <div className="absolute -top-1 -right-1 w-2 h-2 bg-[#00ffff]"></div>
              
              <div className="w-1/2 text-[10px] text-[#00ffff]/80">
                 <div className="flex justify-between text-red-500 mb-2 border-b border-red-500/30 pb-1">
                   <span>sun</span><span>mon</span><span>tue</span><span>wed</span><span>thu</span><span>fri</span><span>sat</span>
                 </div>
                 <div className="grid grid-cols-7 gap-1 text-center">
                    {/* Mock dates */}
                    {Array.from({length: 31}).map((_, i) => (
                      <span key={i} className={i+1 === 15 ? 'text-red-500 font-bold bg-red-500/20' : ''}>
                        {(i + 1).toString().padStart(2, '0')}
                      </span>
                    ))}
                 </div>
              </div>
              <div className="text-right">
                <div className="text-red-500 text-xs tracking-widest flex items-center justify-end gap-2 mb-1">
                  <span>◀</span> FEBRUARY <span>▶</span>
                </div>
                <div className="text-5xl font-bold text-red-500 leading-none mb-1">15</div>
                <div className="text-[#00ffff] tracking-widest text-lg uppercase">friday</div>
              </div>
           </div>

           {/* Main Center Dial */}
           <div className="flex-1 flex flex-col items-center justify-center relative">
              {/* Dial SVG background */}
              <div className="relative w-64 h-64 flex items-center justify-center border-4 border-[#00ffff]/20 rounded-full">
                 <div className="absolute inset-2 border-t-4 border-l-4 border-r-4 border-[#00ffff] rounded-t-full rounded-b-lg"></div>
                 {/* Center Speed */}
                 <div className="text-center mt-8">
                   <div className="text-4xl font-bold text-[#00ffff] tracking-wider">164</div>
                   <div className="text-xs text-[#00ffff]/60">km/h</div>
                 </div>
                 {/* Red Needle */}
                 <div className="absolute inset-0 flex items-center justify-center" style={{ transform: 'rotate(45deg)' }}>
                    <div className="w-1/2 h-0.5 bg-red-500 absolute left-1/2 origin-left -translate-y-1/2 shadow-[0_0_10px_#ff0000]"></div>
                 </div>
              </div>
           </div>

           {/* Lower section of middle column */}
           <div className="h-1/3 flex flex-col gap-4">
              <div className="h-12 border-y border-[#00ffff]/30 flex items-center justify-center gap-1 opacity-70">
                {Array.from({length: 60}).map((_, i) => (
                  <div key={i} className="w-[1px] bg-[#00ffff]" style={{height: `${Math.random() * 80 + 20}%`}}></div>
                ))}
              </div>
              
              <div className="flex-1 flex flex-col items-center justify-center border-y border-[#00ffff]/30 relative py-4">
                <div className="absolute -left-1 -top-1 w-2 h-2 bg-[#00ffff]"></div>
                {/* Sports Car wireframe placeholder */}
                <div className="w-full max-w-[200px] h-20 bg-red-500/20 border border-red-500/50 rounded-[40%] flex items-center justify-center shadow-[0_0_20px_rgba(255,0,0,0.3)]">
                   <span className="text-red-500 tracking-widest text-[10px]">CAR MESH ACTIVE</span>
                </div>
              </div>

              <div className="flex items-end justify-between border-b border-[#00ffff]/30 pb-4 relative">
                <div className="absolute -right-1 bottom-0 w-2 h-2 bg-[#00ffff]"></div>
                <div>
                  <div className="text-3xl text-[#00ffff]">97<span className="text-sm">%</span></div>
                  <div className="text-[9px] text-[#00ffff]/50 uppercase tracking-wider mb-2">oxygen</div>
                  <div className="text-2xl text-red-500">55<span className="text-sm">%</span></div>
                  <div className="text-[9px] text-red-500/50 uppercase tracking-wider">blood</div>
                </div>
                <div className="flex gap-3 h-20">
                  <div className="w-4 bg-gray-800 rounded-t-md relative overflow-hidden"><div className="absolute bottom-0 w-full h-1/2 bg-gray-500"></div></div>
                  <div className="w-4 bg-gray-800 rounded-t-md relative overflow-hidden"><div className="absolute bottom-0 w-full h-4/5 bg-red-600 shadow-[0_0_8px_#ff0000]"></div></div>
                  <div className="w-4 bg-gray-800 rounded-t-md relative overflow-hidden"><div className="absolute bottom-0 w-full h-3/4 bg-gray-500"></div></div>
                  <div className="w-4 bg-gray-800 rounded-t-md relative overflow-hidden"><div className="absolute bottom-0 w-full h-[90%] bg-[#00ffff] shadow-[0_0_8px_#00ffff]"></div></div>
                </div>
              </div>
           </div>

        </div>

        {/* RIGHT COLUMN (Main HUD & Components) (approx 5 cols) */}
        <div className="col-span-5 flex flex-col h-full">
           
           {/* Top Automotive HUD view */}
           <div className="h-[45%] w-full border border-[#00ffff]/30 relative mb-6 overflow-hidden bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/20 via-black to-black">
              {/* Fake city wireframe bg */}
              <div className="absolute inset-0 opacity-20 bg-[linear-gradient(rgba(0,255,255,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,255,0.1)_1px,transparent_1px)] bg-[size:10px_10px]"></div>
              
              <div className="absolute top-2 right-4 text-[#00ffff] text-[10px] tracking-widest">00:18:48:08</div>
              
              <div className="absolute inset-0 flex items-center justify-center gap-12 mt-12">
                 
                 {/* Left Dials */}
                 <div className="relative">
                   <div className="w-40 h-40 rounded-full border-4 border-t-red-600 border-l-red-600 border-b-transparent border-r-transparent rotate-45"></div>
                   <div className="absolute inset-0 flex flex-col items-center justify-center shadow-[inset_0_0_40px_rgba(255,0,0,0.3)] rounded-full">
                      <div className="text-3xl font-bold text-[#00ffff]">204</div>
                      <div className="text-[10px] text-[#00ffff]/60">km/h</div>
                   </div>
                 </div>

                 {/* Center Clock */}
                 <div className="w-16 h-16 rounded-full border-2 border-[#00ffff]/50 absolute top-0">
                    <div className="absolute inset-0 flex items-center justify-center">
                       <div className="w-1/2 h-0.5 bg-red-500 origin-left -rotate-90"></div>
                       <div className="w-1/3 h-0.5 bg-red-500 origin-left rotate-45"></div>
                    </div>
                 </div>

                 {/* Right Dials */}
                 <div className="relative">
                   <div className="w-40 h-40 rounded-full border-4 border-t-red-600 border-r-red-600 border-b-transparent border-l-transparent -rotate-45"></div>
                   <div className="absolute inset-0 flex flex-col items-center justify-center shadow-[inset_0_0_40px_rgba(255,0,0,0.3)] rounded-full">
                      <div className="text-4xl font-bold text-white shadow-[0_0_10px_#fff]">D</div>
                   </div>
                 </div>

              </div>

              {/* Red road perspective lines */}
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-full h-1/3 overflow-hidden">
                 <div className="absolute bottom-0 left-[20%] w-[2px] h-[200%] bg-red-600 origin-bottom transform rotate-[60deg] shadow-[0_0_15px_#ff0000]"></div>
                 <div className="absolute bottom-0 right-[20%] w-[2px] h-[200%] bg-red-600 origin-bottom transform -rotate-[60deg] shadow-[0_0_15px_#ff0000]"></div>
              </div>
           </div>

           {/* Bottom Details Panel */}
           <div className="flex-1 grid grid-cols-3 grid-rows-2 gap-4">
              
              <div className="border border-[#00ffff]/20 flex flex-col items-center justify-center p-2 relative group hover:border-[#00ffff]/80 transition-colors">
                <div className="absolute -top-1 -left-1 w-2 h-2 bg-red-500"></div>
                <div className="w-20 h-20 rounded-full border border-[#00ffff]/40 bg-[#00ffff]/5 flex items-center justify-center">
                   <div className="text-[10px] text-[#00ffff]">HELMET</div>
                </div>
              </div>

              <div className="border border-[#00ffff]/20 p-2 col-span-2 relative">
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-[#00ffff]"></div>
                <div className="flex justify-between text-[10px] text-[#00ffff] h-full">
                  <div className="flex flex-col gap-1 w-1/3 font-mono opacity-80">
                     <span>02031</span><span>01828</span><span>01930</span><span>01727</span><span>01889</span>
                  </div>
                  <div className="flex-1 flex justify-center gap-2 items-center">
                     {/* Suspension elements mock */}
                     {Array.from({length: 4}).map((_, i) => (
                       <div key={i} className="w-4 h-16 border border-[#00ffff]/50 rounded-sm relative">
                         <div className="absolute inset-x-0 bottom-0 bg-[#00ffff]/30" style={{height: `${Math.random() * 50 + 20}%`}}></div>
                       </div>
                     ))}
                  </div>
                  <div className="flex flex-col gap-1 w-1/3 font-mono text-right text-red-400">
                     <span>01970</span><span>01991</span><span>02234</span><span>01798</span><span>02021</span>
                  </div>
                </div>
              </div>

              <div className="border border-[#00ffff]/20 flex flex-col items-center justify-center p-4 relative">
                <div className="absolute -bottom-1 -left-1 w-2 h-2 bg-red-500"></div>
                <div className="text-[#00ffff] text-[10px] tracking-widest mb-1">SPEED</div>
                <div className="text-4xl font-bold text-red-600">241</div>
              </div>

              <div className="border border-[#00ffff]/20 p-4 relative col-span-2 flex flex-col gap-2">
                 <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-[#00ffff]"></div>
                 {/* Keyboard */}
                 <div className="grid grid-cols-12 gap-1 flex-1 text-[8px] text-center">
                   {'1234567890-='.split('').map((k,i) => <div key={i} className="border border-[#00ffff]/30 flex items-center justify-center bg-[#00ffff]/5">{k}</div>)}
                   {'qwertyuiop[]'.split('').map((k,i) => <div key={i} className="border border-[#00ffff]/30 flex items-center justify-center bg-[#00ffff]/5 uppercase">{k}</div>)}
                   {'asdfghjkl;\''.split('').map((k,i) => <div key={i} className={`border border-[#00ffff]/30 flex items-center justify-center uppercase ${k==='s' ? 'bg-red-600 text-white border-red-600' : 'bg-[#00ffff]/5'}`}>{k}</div>)}
                 </div>
                 {/* Sector Bars */}
                 <div className="flex flex-col gap-2 mt-2">
                    {[
                      {label: 'Sector 1', val: '72%', c: 'bg-[#00ffff]'},
                      {label: 'Sector 2', val: '92%', c: 'bg-red-600'},
                      {label: 'Sector 3', val: '61%', c: 'bg-[#00ffff]'}
                    ].map((s, i) => (
                      <div key={i} className="flex items-center gap-2 text-[9px] text-[#00ffff]">
                        <span className="w-12">{s.label}</span>
                        <div className="flex-1 h-1.5 bg-gray-900 border border-[#00ffff]/20 relative">
                          <div className={`absolute top-0 left-0 h-full ${s.c}`} style={{width: s.val}}></div>
                        </div>
                        <span className="w-6 text-right">{s.val}</span>
                      </div>
                    ))}
                 </div>
              </div>

           </div>
        </div>

      </div>
    </div>
  );
}
