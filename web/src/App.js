import './App.css';

import { useEffect, useMemo, useState } from 'react';
import { useSortBy, useTable } from 'react-table';

function App() {
  const [data, setData] = useState([]);
  useEffect(() => {
    fetch('data.csv').then((res) => {
      res.text().then((txt) => {
        const lines = txt.split("\n");
        setData(lines.map((line) => {
          const dt = line.split(';');
          return { name: dt[0], parts: dt[1], holes: dt[2], totallength: dt[3], longest: dt[4] };
        }));
      });
    });
  }, []);

  const columns = useMemo(() => 
    [
      {
        Header: 'Country',
        accessor: 'name'
      },
      {
        Header: 'Parts',
        accessor: 'parts'
      },
      {
        Header: 'Holes',
        accessor: 'holes'
      },
      {
        Header: 'Total border length',
        accessor: 'totallength'
      },
      {
        Header: 'Longest contiguous border length',
        accessor: 'longest'
      },
    ], []);

  const tableInstance = useTable({ columns, data }, useSortBy);
  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
  } = tableInstance;

  return (
    <div className="App">
  <table {...getTableProps()}>
     <thead>
       {// Loop over the header rows
       headerGroups.map(headerGroup => (
         // Apply the header row props
         <tr {...headerGroup.getHeaderGroupProps()}>
           {// Loop over the headers in each row
           headerGroup.headers.map(column => (
             // Apply the header cell props
             <th {...column.getHeaderProps(column.getSortByToggleProps())}>
               {// Render the header
               column.render('Header')}
               <span>
                 {column.isSorted ? (column.isSortedDesc ? ' 🔽' : ' 🔼') : ''}
               </span>
             </th>
           ))}
         </tr>
       ))}
     </thead>
     {/* Apply the table body props */}
     <tbody {...getTableBodyProps()}>
       {// Loop over the table rows
       rows.map(row => {
         // Prepare the row for display
         prepareRow(row)
         return (
           // Apply the row props
           <tr {...row.getRowProps()}>
             {// Loop over the rows cells
             row.cells.map(cell => {
               // Apply the cell props
               return (
                 <td {...cell.getCellProps()}>
                   {// Render the cell contents
                   cell.render('Cell')}
                 </td>
               )
             })}
           </tr>
         )
       })}
     </tbody>
   </table>
    </div>
  );
}

export default App;
