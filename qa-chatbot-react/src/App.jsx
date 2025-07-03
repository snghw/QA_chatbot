import React, { useState, useEffect } from "react";
import { MessageCircle, Send, Car, Book, User, Bot, Loader, CheckCircle, AlertCircle, Plus, ExternalLink } from "lucide-react";
import { marked } from 'marked';

// ✅ .env에서 불러오기
// const BASE_URL = "https://qa-backend-faiss.fly.dev";
const BASE_URL = "http://localhost:8080"

// marked 설정
marked.setOptions({
  headerIds: false,
  mangle: false,
  breaks: true
});

function App() {
  const [question, setQuestion] = useState("");
  const [selectedVehicle, setSelectedVehicle] = useState("");
  const [availableVehicles, setAvailableVehicles] = useState([]);
  const [allVehicles, setAllVehicles] = useState(["SONATA", "SANTAFE", "TUCSON", "AVANTE", "GRANDEUR", "PALISADE", "KONA"]);
  const [vehicleSelectionStep, setVehicleSelectionStep] = useState(true);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(""); // 로딩 단계 표시

  // 차량 목록 불러오기
  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    try {
      const res = await fetch(`${BASE_URL}/vehicles`);
      const data = await res.json();
      setAllVehicles(data.vehicles);
      setAvailableVehicles(data.available_vehicles);
    } catch (error) {
      console.error('차량 목록 로드 오류:', error);
    }
  };

  const selectVehicle = (vehicle) => {
    setSelectedVehicle(vehicle);
    setVehicleSelectionStep(false);
    setMessages([
      {
        type: "bot",
        content: `안녕하세요! **${vehicle}** 매뉴얼 QA 어시스턴트입니다. 차량 관련 궁금한 점을 언제든 물어보세요.`,
        timestamp: new Date()
      }
    ]);
  };

  const changeVehicle = () => {
    setVehicleSelectionStep(true);
    setSelectedVehicle("");
    setMessages([]);
    setQuestion("");
  };

  const handleManualUpload = (vehicle) => {
    // 나중에 구현할 매뉴얼 등록 기능
    alert(`${vehicle} 매뉴얼 등록 기능은 곧 추가될 예정입니다.`);
  };

  const openOfficialManual = () => {
    window.open('https://ownersmanual.hyundai.com/main?langCode=ko_KR&countryCode=A99', '_blank');
  };

  const ask = async () => {
    if (!question.trim() || !selectedVehicle) return;
    
    const userMessage = {
      type: "user", 
      content: question,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setQuestion("");
    setLoading(true);
    setLoadingStep("매뉴얼 검색 중...");

    try {
      const res = await fetch(`${BASE_URL}/ask`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ 
          q: question,
          vehicle: selectedVehicle 
        })
      });
      
      setLoadingStep("답변 생성 중...");
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      
      const botMessage = {
        type: "bot",
        content: data.answer,
        timestamp: new Date(),
        sources: data.sources || []
      };
      
      setMessages(prev => [...prev, botMessage]);
      setLoading(false);
      setLoadingStep("");
      
    } catch (error) {
      console.error('API 요청 오류:', error);
      const errorMessage = {
        type: "bot",
        content: `죄송합니다. 오류가 발생했습니다: ${error.message}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      setLoading(false);
      setLoadingStep("");
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  };

  // 차량 선택 화면
  if (vehicleSelectionStep) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
        {/* 🔥 고정 헤더 - sticky 클래스 추가 */}
        <div className="sticky top-0 z-50 bg-gradient-to-r from-blue-600 to-blue-700 shadow-lg">
          <div className="max-w-4xl mx-auto px-6 py-4">
            <div className="flex items-center space-x-3">
              <div className="bg-white p-2 rounded-lg shadow-sm">
                <Car className="w-8 h-8 text-blue-600" />
              </div>
              <div>
                <button
                  onClick={changeVehicle}
                  className="flex items-center space-x-1 group transition duration-300"
                >
                  <span className="text-2xl font-bold text-white group-hover:text-gray-300 transition duration-300">
                    HYUNDAI
                  </span>
                </button>
                <p className="text-blue-100 text-sm">Vehicle Manual Assistant</p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content - 헤더 높이만큼 패딩 추가 */}
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
            
            {/* 매뉴얼이 없는 경우 메인 메시지 */}
            {availableVehicles.length === 0 ? (
              <>
                <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-6 border-b">
                  <h2 className="text-xl font-bold text-gray-800 mb-2">현대자동차 매뉴얼 QA 시스템</h2>
                  <p className="text-gray-600">AI 기반 차량 매뉴얼 질의응답 서비스</p>
                </div>

                <div className="p-8 text-center">
                  <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Book className="w-10 h-10 text-blue-600" />
                  </div>
                  
                  <h3 className="text-2xl font-bold text-gray-800 mb-4">매뉴얼 등록이 필요합니다</h3>
                  <p className="text-gray-600 mb-8 max-w-md mx-auto leading-relaxed">
                    아직 등록된 차량 매뉴얼이 없습니다.<br />
                    아래 방법으로 매뉴얼을 확인하거나 등록해주세요.
                  </p>

                  {/* 액션 버튼들 */}
                  <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                    <button
                      onClick={openOfficialManual}
                      className="inline-flex items-center justify-center space-x-3 bg-blue-600 hover:bg-blue-700 text-white font-medium px-8 py-4 rounded-xl shadow-lg transition-all duration-200 hover:shadow-xl hover:scale-105"
                    >
                      <ExternalLink className="w-6 h-6" />
                      <span>현대자동차 공식 매뉴얼 사이트</span>
                    </button>
                    
                    <button
                      onClick={() => alert('매뉴얼 업로드 기능은 곧 추가될 예정입니다.')}
                      className="inline-flex items-center justify-center space-x-3 bg-gray-600 hover:bg-gray-700 text-white font-medium px-8 py-4 rounded-xl shadow-lg transition-all duration-200 hover:shadow-xl hover:scale-105"
                    >
                      <Plus className="w-6 h-6" />
                      <span>새 매뉴얼 등록하기</span>
                    </button>
                  </div>

                  {/* 지원 차량 목록 */}
                  <div className="bg-gray-50 rounded-xl p-6">
                    <h4 className="text-lg font-semibold text-gray-800 mb-4">지원 예정 차량</h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                      {allVehicles.map((vehicle) => (
                        <div
                          key={vehicle}
                          className="bg-white border-2 border-gray-200 rounded-lg p-3 text-center"
                        >
                          <div className="flex items-center justify-center space-x-2">
                            <Car className="w-4 h-4 text-gray-400" />
                            <span className="font-medium text-gray-700">{vehicle}</span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">준비 중</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 안내 메시지 */}
                  <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-start space-x-3">
                      <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                      <div className="text-left">
                        <h5 className="font-semibold text-blue-800 mb-1">매뉴얼 등록 안내</h5>
                        <p className="text-sm text-blue-700">
                          • 현재 매뉴얼 자동 등록 기능을 개발 중입니다<br />
                          • 공식 현대자동차 매뉴얼 사이트에서 차량별 매뉴얼을 확인하실 수 있습니다<br />
                          • 등록 기능 완료 시 이메일로 안내드리겠습니다
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 추가 컨텐츠 - 스크롤 테스트용 */}
                <div className="p-8 bg-gray-50">
                  <h4 className="text-lg font-semibold mb-4">서비스 특징</h4>
                  <div className="grid md:grid-cols-3 gap-6">
                    <div className="text-center">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg mx-auto mb-3 flex items-center justify-center">
                        <Bot className="w-6 h-6 text-blue-600" />
                      </div>
                      <h5 className="font-semibold mb-2">AI 기반 답변</h5>
                      <p className="text-sm text-gray-600">최신 AI 기술로 정확한 답변을 제공합니다.</p>
                    </div>
                    <div className="text-center">
                      <div className="w-12 h-12 bg-green-100 rounded-lg mx-auto mb-3 flex items-center justify-center">
                        <Book className="w-6 h-6 text-green-600" />
                      </div>
                      <h5 className="font-semibold mb-2">공식 매뉴얼 기반</h5>
                      <p className="text-sm text-gray-600">현대자동차 공식 매뉴얼만을 사용합니다.</p>
                    </div>
                    <div className="text-center">
                      <div className="w-12 h-12 bg-purple-100 rounded-lg mx-auto mb-3 flex items-center justify-center">
                        <MessageCircle className="w-6 h-6 text-purple-600" />
                      </div>
                      <h5 className="font-semibold mb-2">24/7 지원</h5>
                      <p className="text-sm text-gray-600">언제든지 궁금한 점을 물어보세요.</p>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              /* 매뉴얼이 있는 경우 차량 선택 UI */
              <>
                <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-6 border-b">
                  <h2 className="text-xl font-bold text-gray-800 mb-2">차량을 선택해주세요</h2>
                  <p className="text-gray-600">질문하실 차량의 매뉴얼을 선택해주세요.</p>
                </div>

                <div className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {allVehicles.map((vehicle) => {
                      const isAvailable = availableVehicles.includes(vehicle);
                      
                      return (
                        <div
                          key={vehicle}
                          className={`p-4 rounded-xl border-2 transition-all duration-200 ${
                            isAvailable
                              ? 'border-gray-200 bg-white hover:border-blue-400 hover:shadow-lg hover:bg-blue-50 cursor-pointer'
                              : 'border-gray-100 bg-gray-50'
                          }`}
                          onClick={() => isAvailable && selectVehicle(vehicle)}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <h3 className="font-semibold text-gray-800">{vehicle}</h3>
                            {isAvailable ? (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            ) : (
                              <AlertCircle className="w-5 h-5 text-gray-400" />
                            )}
                          </div>
                          <p className={`text-sm ${isAvailable ? 'text-gray-600' : 'text-gray-400'}`}>
                            {isAvailable ? '매뉴얼 사용 가능' : '매뉴얼 준비 중'}
                          </p>
                          
                          {!isAvailable && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleManualUpload(vehicle);
                              }}
                              className="w-full mt-3 bg-gray-600 hover:bg-gray-700 text-white py-2 px-4 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
                            >
                              <Plus className="w-4 h-4" />
                              <span>매뉴얼 등록하기</span>
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  
                  {/* 공식 홈페이지 및 매뉴얼 등록 버튼 */}
                  <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
                    <button
                      onClick={openOfficialManual}
                      className="inline-flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-3 rounded-xl shadow-lg transition-all duration-200 hover:shadow-xl"
                    >
                      <ExternalLink className="w-5 h-5" />
                      <span>현대자동차 공식 매뉴얼 사이트</span>
                    </button>
                    
                    <button
                      onClick={() => alert('매뉴얼 업로드 기능은 곧 추가될 예정입니다.')}
                      className="inline-flex items-center justify-center space-x-2 bg-gray-600 hover:bg-gray-700 text-white font-medium px-6 py-3 rounded-xl shadow-lg transition-all duration-200 hover:shadow-xl"
                    >
                      <Plus className="w-5 h-5" />
                      <span>새 매뉴얼 등록하기</span>
                    </button>
                  </div>
                </div>

                {/* 매뉴얼 등록 안내 - 매뉴얼이 있는 경우에도 표시 */}
                <div className="p-6 bg-blue-50 border-t border-blue-100">
                  <div className="flex items-start space-x-3">
                    <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                    <div className="text-left">
                      <h5 className="font-semibold text-blue-800 mb-1">매뉴얼 등록 안내</h5>
                      <p className="text-sm text-blue-700">
                        • 현재 매뉴얼 자동 등록 기능을 개발 중입니다<br />
                        • 공식 현대자동차 매뉴얼 사이트에서 차량별 매뉴얼을 확인하실 수 있습니다<br />
                        • 등록 기능 완료 시 이메일로 안내드리겠습니다
                      </p>
                    </div>
                  </div>
                </div>

                {/* 서비스 특징 - 매뉴얼이 있는 경우에도 표시 */}
                <div className="p-8 bg-gray-50">
                  <h4 className="text-lg font-semibold mb-4 text-center">서비스 특징</h4>
                  <div className="grid md:grid-cols-3 gap-6">
                    <div className="text-center">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg mx-auto mb-3 flex items-center justify-center">
                        <Bot className="w-6 h-6 text-blue-600" />
                      </div>
                      <h5 className="font-semibold mb-2">AI 기반 답변</h5>
                      <p className="text-sm text-gray-600">최신 AI 기술로 정확한 답변을 제공합니다.</p>
                    </div>
                    <div className="text-center">
                      <div className="w-12 h-12 bg-green-100 rounded-lg mx-auto mb-3 flex items-center justify-center">
                        <Book className="w-6 h-6 text-green-600" />
                      </div>
                      <h5 className="font-semibold mb-2">공식 매뉴얼 기반</h5>
                      <p className="text-sm text-gray-600">현대자동차 공식 매뉴얼만을 사용합니다.</p>
                    </div>
                    <div className="text-center">
                      <div className="w-12 h-12 bg-purple-100 rounded-lg mx-auto mb-3 flex items-center justify-center">
                        <MessageCircle className="w-6 h-6 text-purple-600" />
                      </div>
                      <h5 className="font-semibold mb-2">24/7 지원</h5>
                      <p className="text-sm text-gray-600">언제든지 궁금한 점을 물어보세요.</p>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  // 채팅 화면
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* 🔥 고정 헤더 - sticky 클래스 추가 */}
      <div className="sticky top-0 z-50 bg-gradient-to-r from-blue-600 to-blue-700 shadow-lg">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-white p-2 rounded-lg shadow-sm">
                <Car className="w-8 h-8 text-blue-600" />
              </div>
              <div>
                <button
                  onClick={changeVehicle}
                  className="flex items-center space-x-1 group transition duration-300"
                >
                  <span className="text-2xl font-bold text-white group-hover:text-gray-300 transition duration-300">
                    HYUNDAI
                  </span>
                </button>
                <p className="text-blue-100 text-sm">Vehicle Manual Assistant</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="text-right">
                <p className="text-white font-semibold">{selectedVehicle}</p>
                <p className="text-blue-100 text-sm">선택된 차량</p>
              </div>
              <button
                onClick={changeVehicle}
                className="bg-white/20 hover:bg-white/30 text-white px-3 py-1 rounded-lg text-sm transition-colors"
              >
                차량 변경
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - 헤더가 고정되어 있으므로 패딩 조정 */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          {/* Chat Header */}
          <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4 border-b">
            <div className="flex items-center space-x-3">
              <Book className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-800">{selectedVehicle} 매뉴얼 QA</h2>
              <div className="ml-auto flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-sm text-gray-600">온라인</span>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="h-96 overflow-y-auto p-6 space-y-4 bg-gray-50">
            {messages.map((message, index) => (
              <div key={index} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex items-start space-x-3 max-w-xs sm:max-w-md lg:max-w-2xl ${message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    message.type === 'user' 
                      ? 'bg-blue-600' 
                      : 'bg-gradient-to-r from-gray-600 to-gray-700'
                  }`}>
                    {message.type === 'user' ? (
                      <User className="w-4 h-4 text-white" />
                    ) : (
                      <Bot className="w-4 h-4 text-white" />
                    )}
                  </div>
                  <div className={`px-4 py-3 rounded-2xl shadow-sm ${
                    message.type === 'user'
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-white text-gray-800 rounded-bl-sm border'
                  }`}>
                    {message.type === 'bot' ? (
                      <div 
                        className="text-sm leading-relaxed
                          [&>h1]:text-lg [&>h1]:font-bold [&>h1]:text-gray-800 [&>h1]:mb-3 [&>h1]:flex [&>h1]:items-center
                          [&>h2]:text-base [&>h2]:font-semibold [&>h2]:text-gray-700 [&>h2]:mt-4 [&>h2]:mb-2 [&>h2]:flex [&>h2]:items-center
                          [&>h3]:text-sm [&>h3]:font-semibold [&>h3]:text-gray-700 [&>h3]:mt-3 [&>h3]:mb-2 [&>h3]:flex [&>h3]:items-center
                          [&>p]:mb-2 [&>p]:leading-relaxed
                          [&>strong]:font-semibold [&>strong]:text-blue-600
                          [&>blockquote]:border-l-4 [&>blockquote]:border-blue-400 [&>blockquote]:bg-blue-50 [&>blockquote]:pl-4 [&>blockquote]:py-2 [&>blockquote]:my-3 [&>blockquote]:rounded-r-lg
                          [&>hr]:my-4 [&>hr]:border-gray-200
                          [&>em]:text-gray-600 [&>em]:text-xs
                          [&>ul]:list-disc [&>ul]:pl-5 [&>ul]:mb-2
                          [&>ol]:list-decimal [&>ol]:pl-5 [&>ol]:mb-2
                          [&>li]:mb-1"
                        dangerouslySetInnerHTML={{ __html: marked(message.content) }}
                      />
                    ) : (
                      <p className="text-sm leading-relaxed">{message.content}</p>
                    )}
                    
                    <p className={`text-xs mt-2 ${
                      message.type === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}>
                      {message.timestamp.toLocaleTimeString('ko-KR', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-start space-x-3 max-w-xs">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-gray-600 to-gray-700 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-white border shadow-sm">
                    <div className="flex items-center space-x-2">
                      <Loader className="w-4 h-4 animate-spin text-gray-600" />
                      <p className="text-sm text-gray-600">{loadingStep || "답변을 생성하고 있습니다..."}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="border-t bg-white p-6">
            <div className="flex space-x-4">
              <div className="flex-1 relative">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={`${selectedVehicle} 매뉴얼에 대해 궁금한 점을 입력하세요... (예: 엔진오일 교환 방법은?)`}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none resize-none transition-colors"
                  rows="2"
                  disabled={loading}
                />
                <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                  {question.length}/500
                </div>
              </div>
              <button
                onClick={ask}
                disabled={loading || !question.trim()}
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-300 disabled:to-gray-400 text-white p-3 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl disabled:cursor-not-allowed flex items-center justify-center min-w-[60px]"
              >
                {loading ? (
                  <Loader className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            
            {/* Quick Actions */}
            <div className="mt-4 flex flex-wrap gap-2">
              <button 
                onClick={() => setQuestion("엔진오일 교환 방법을 알려주세요")}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full transition-colors text-gray-700"
              >
                🛢️ 엔진오일 교환
              </button>
              <button 
                onClick={() => setQuestion("타이어 공기압 점검 방법을 알려주세요")}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full transition-colors text-gray-700"
              >
                🚗 타이어 점검
              </button>
              <button 
                onClick={() => setQuestion("배터리 점검은 어떻게 하나요?")}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full transition-colors text-gray-700"
              >
                🔋 배터리 점검
              </button>
              <button 
                onClick={() => setQuestion("정기 점검 주기를 알려주세요")}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full transition-colors text-gray-700"
              >
                🔧 정기 점검
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-gray-500 text-sm">
            © 2025 현대자동차. 이 챗봇은 {selectedVehicle} 공식 매뉴얼을 기반으로 정보를 제공합니다.
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;