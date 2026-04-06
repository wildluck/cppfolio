#include <crow.h>
#include <cstdint>
#include <cstdlib>
#include <string>

#include "generated/pages.hpp"

template<std::size_t N>
crow::response html_response(const fixed_string<N>& page)
{
    crow::response res{ 200, std::string(page.sv()) };
    res.set_header("Content-Type", "text/html; charset=utf-8");
    return res;
}

int main()
{
    crow::SimpleApp app;

    CROW_ROUTE(app, "/")([]() {
        return html_response(blog::pages::index);
    });

    // all post routes registered automatically by codegen
    blog::pages::register_routes(app);

    CROW_ROUTE(app, "/healthz")([]() {
        return crow::response{200, "ok"};
    });

    const char* port_env = std::getenv("PORT");
    const uint16_t port = port_env
        ? static_cast<uint16_t>(std::stoi(port_env))
        : 8080;

    app.loglevel(crow::LogLevel::Info)
       .port(port)
       .multithreaded()
       .run();
}
