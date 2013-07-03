cmake_minimum_required(VERSION 2.8)
project(kochipylli)

find_package(PythonInterp REQUIRED)

set(sources
  contextparser.py
  main.py
  mainwindow.py
  service.py
)

set(objects)
foreach(source ${sources})
  set(out "${CMAKE_CURRENT_SOURCE_DIR}/${source}c")
  add_custom_command(OUTPUT ${out} DEPENDS ${source}
    VERBATIM COMMAND ${PYTHON_EXECUTABLE}
      -c "import py_compile; py_compile.main()"
      ${source}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  )
  list(APPEND objects "${out}")
endforeach()

add_custom_target(compile ALL DEPENDS ${objects})
