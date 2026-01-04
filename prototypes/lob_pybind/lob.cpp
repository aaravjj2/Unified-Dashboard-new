#include <pybind11/pybind11.h>
#include <string>

namespace py = pybind11;

class LOB {
public:
    LOB() {}
    std::string status() { return "proto-lob:ok"; }
};

PYBIND11_MODULE(lob_proto, m) {
    py::class_<LOB>(m, "LOB")
        .def(py::init<>())
        .def("status", &LOB::status);
}
