import HCPForm from "../components/HCPForm";
import AIChat from "../components/AIChat";

function Dashboard() {
  return (
    <div
      className="min-h-screen w-full bg-slate-100"
      style={{ paddingTop: "24px", paddingLeft: "40px", paddingRight: "40px" }}
    >
      <div className="w-full box-border pt-14 pb-12">
        <div className="grid grid-cols-12 gap-6 md:gap-8">
          {/* Left Side */}
          <div className="col-span-12 md:col-span-7">
            <div className="bg-white rounded-2xl shadow-md border border-gray-200 h-[85vh] overflow-y-auto">
              <HCPForm />
            </div>
          </div>

          {/* Right Side */}
          <div className="col-span-12 md:col-span-5">
            <div className="bg-white rounded-2xl shadow-md border border-gray-200 h-[85vh] flex flex-col">
              <AIChat />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;